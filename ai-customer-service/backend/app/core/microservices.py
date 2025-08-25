"""
Microservices Configuration

This module provides configuration and utilities for decomposing the monolithic
application into microservices.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import aiohttp
import logging
from urllib.parse import urljoin

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Types of microservices."""
    USER_SERVICE = "user-service"
    CHAT_SERVICE = "chat-service"
    AI_SERVICE = "ai-service"
    ANALYTICS_SERVICE = "analytics-service"
    NOTIFICATION_SERVICE = "notification-service"
    GATEWAY_SERVICE = "api-gateway"


@dataclass
class ServiceConfig:
    """Configuration for a microservice."""
    name: str
    host: str
    port: int
    health_endpoint: str = "/health"
    timeout: int = 30
    retries: int = 3
    circuit_breaker_threshold: int = 5
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def health_url(self) -> str:
        return urljoin(self.base_url, self.health_endpoint)


class ServiceRegistry:
    """Service registry for microservices discovery."""
    
    def __init__(self):
        self._services: Dict[str, ServiceConfig] = {}
        self._circuit_breakers: Dict[str, int] = {}
    
    def register_service(self, service_type: ServiceType, config: ServiceConfig):
        """Register a service in the registry."""
        self._services[service_type.value] = config
        self._circuit_breakers[service_type.value] = 0
        logger.info(f"Registered service: {service_type.value} at {config.base_url}")
    
    def get_service(self, service_type: ServiceType) -> Optional[ServiceConfig]:
        """Get service configuration."""
        return self._services.get(service_type.value)
    
    def is_circuit_open(self, service_type: ServiceType) -> bool:
        """Check if circuit breaker is open for a service."""
        service_name = service_type.value
        if service_name not in self._circuit_breakers:
            return False
        
        config = self._services.get(service_name)
        if not config:
            return True
        
        return self._circuit_breakers[service_name] >= config.circuit_breaker_threshold
    
    def record_failure(self, service_type: ServiceType):
        """Record a service failure."""
        service_name = service_type.value
        self._circuit_breakers[service_name] = self._circuit_breakers.get(service_name, 0) + 1
        logger.warning(f"Service failure recorded for {service_name}: {self._circuit_breakers[service_name]}")
    
    def record_success(self, service_type: ServiceType):
        """Record a service success."""
        service_name = service_type.value
        if service_name in self._circuit_breakers:
            self._circuit_breakers[service_name] = max(0, self._circuit_breakers[service_name] - 1)
    
    def reset_circuit_breaker(self, service_type: ServiceType):
        """Reset circuit breaker for a service."""
        service_name = service_type.value
        self._circuit_breakers[service_name] = 0
        logger.info(f"Circuit breaker reset for {service_name}")
    
    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services."""
        return [
            {
                "name": config.name,
                "type": service_type,
                "base_url": config.base_url,
                "circuit_breaker_failures": self._circuit_breakers.get(service_type, 0),
                "circuit_open": self.is_circuit_open(ServiceType(service_type))
            }
            for service_type, config in self._services.items()
        ]


class ServiceClient:
    """HTTP client for making requests to microservices."""
    
    def __init__(self, registry: ServiceRegistry):
        self._registry = registry
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def request(
        self,
        service_type: ServiceType,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to a microservice."""
        
        # Check circuit breaker
        if self._registry.is_circuit_open(service_type):
            raise ServiceUnavailableError(f"Circuit breaker open for {service_type.value}")
        
        # Get service configuration
        config = self._registry.get_service(service_type)
        if not config:
            raise ServiceNotFoundError(f"Service not registered: {service_type.value}")
        
        url = urljoin(config.base_url, endpoint)
        
        # Prepare request
        request_kwargs = {
            "url": url,
            "method": method.upper(),
            "timeout": aiohttp.ClientTimeout(total=config.timeout)
        }
        
        if data:
            request_kwargs["json"] = data
        if params:
            request_kwargs["params"] = params
        if headers:
            request_kwargs["headers"] = headers
        
        # Retry logic
        last_exception = None
        for attempt in range(config.retries + 1):
            try:
                if not self._session:
                    self._session = aiohttp.ClientSession()
                
                async with self._session.request(**request_kwargs) as response:
                    if response.status >= 200 and response.status < 300:
                        self._registry.record_success(service_type)
                        return await response.json()
                    else:
                        raise ServiceError(
                            f"Service returned {response.status}: {await response.text()}"
                        )
            
            except Exception as e:
                last_exception = e
                logger.warning(f"Request to {service_type.value} failed (attempt {attempt + 1}): {e}")
                
                if attempt < config.retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All retries failed
        self._registry.record_failure(service_type)
        raise last_exception
    
    async def get(self, service_type: ServiceType, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a GET request."""
        return await self.request(service_type, "GET", endpoint, **kwargs)
    
    async def post(self, service_type: ServiceType, endpoint: str, data: Dict, **kwargs) -> Dict[str, Any]:
        """Make a POST request."""
        return await self.request(service_type, "POST", endpoint, data=data, **kwargs)
    
    async def put(self, service_type: ServiceType, endpoint: str, data: Dict, **kwargs) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self.request(service_type, "PUT", endpoint, data=data, **kwargs)
    
    async def delete(self, service_type: ServiceType, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self.request(service_type, "DELETE", endpoint, **kwargs)


class ServiceError(Exception):
    """Base exception for service errors."""
    pass


class ServiceNotFoundError(ServiceError):
    """Exception raised when a service is not found."""
    pass


class ServiceUnavailableError(ServiceError):
    """Exception raised when a service is unavailable."""
    pass


class MicroserviceOrchestrator:
    """Orchestrates operations across multiple microservices."""
    
    def __init__(self, registry: ServiceRegistry):
        self._registry = registry
    
    async def health_check_all_services(self) -> Dict[str, Any]:
        """Perform health checks on all registered services."""
        results = {}
        
        async with ServiceClient(self._registry) as client:
            for service_type, config in self._registry._services.items():
                try:
                    result = await client.get(
                        ServiceType(service_type),
                        config.health_endpoint
                    )
                    results[service_type] = {
                        "status": "healthy",
                        "response": result
                    }
                except Exception as e:
                    results[service_type] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
        
        return results
    
    async def distributed_transaction(
        self,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a distributed transaction across multiple services."""
        # Simple saga pattern implementation
        completed_operations = []
        rollback_operations = []
        
        try:
            async with ServiceClient(self._registry) as client:
                for operation in operations:
                    service_type = ServiceType(operation["service"])
                    method = operation["method"]
                    endpoint = operation["endpoint"]
                    data = operation.get("data", {})
                    
                    result = await client.request(
                        service_type, method, endpoint, data=data
                    )
                    
                    completed_operations.append({
                        "operation": operation,
                        "result": result
                    })
                    
                    # Store rollback information if provided
                    if "rollback" in operation:
                        rollback_operations.append(operation["rollback"])
            
            return {
                "status": "success",
                "operations": completed_operations
            }
        
        except Exception as e:
            # Execute rollback operations
            logger.error(f"Distributed transaction failed: {e}")
            
            await self._execute_rollback(rollback_operations)
            
            return {
                "status": "failed",
                "error": str(e),
                "completed_operations": completed_operations
            }
    
    async def _execute_rollback(self, rollback_operations: List[Dict[str, Any]]):
        """Execute rollback operations in reverse order."""
        async with ServiceClient(self._registry) as client:
            for operation in reversed(rollback_operations):
                try:
                    service_type = ServiceType(operation["service"])
                    method = operation["method"]
                    endpoint = operation["endpoint"]
                    data = operation.get("data", {})
                    
                    await client.request(service_type, method, endpoint, data=data)
                    logger.info(f"Rollback completed for {operation}")
                
                except Exception as e:
                    logger.error(f"Rollback failed for {operation}: {e}")


# Global service registry
service_registry = ServiceRegistry()

# Configure default services for monolithic deployment
def configure_default_services():
    """Configure default service endpoints for monolithic deployment."""
    
    base_host = getattr(settings, 'SERVICE_HOST', 'localhost')
    base_port = getattr(settings, 'SERVICE_PORT', 8000)
    
    # All services point to the same instance in monolithic mode
    service_registry.register_service(
        ServiceType.USER_SERVICE,
        ServiceConfig("user-service", base_host, base_port)
    )
    
    service_registry.register_service(
        ServiceType.CHAT_SERVICE,
        ServiceConfig("chat-service", base_host, base_port)
    )
    
    service_registry.register_service(
        ServiceType.AI_SERVICE,
        ServiceConfig("ai-service", base_host, base_port)
    )
    
    service_registry.register_service(
        ServiceType.ANALYTICS_SERVICE,
        ServiceConfig("analytics-service", base_host, base_port)
    )
    
    service_registry.register_service(
        ServiceType.NOTIFICATION_SERVICE,
        ServiceConfig("notification-service", base_host, base_port)
    )
    
    logger.info("Default services configured for monolithic deployment")


def configure_microservices():
    """Configure service endpoints for microservices deployment."""
    
    # These would typically come from environment variables or config files
    microservices_config = getattr(settings, 'MICROSERVICES_CONFIG', {})
    
    for service_name, config in microservices_config.items():
        try:
            service_type = ServiceType(service_name)
            service_config = ServiceConfig(
                name=config["name"],
                host=config["host"],
                port=config["port"],
                health_endpoint=config.get("health_endpoint", "/health"),
                timeout=config.get("timeout", 30),
                retries=config.get("retries", 3)
            )
            service_registry.register_service(service_type, service_config)
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid microservice configuration for {service_name}: {e}")
    
    logger.info("Microservices configuration loaded")


# Initialize with default configuration
configure_default_services()
