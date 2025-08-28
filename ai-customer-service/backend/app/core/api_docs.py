"""
Enhanced API Documentation and Testing Framework

This module provides comprehensive API documentation, testing utilities,
and interactive API exploration tools.
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import uuid

from app.core.config import settings


class HTTPMethod(Enum):
    """HTTP methods for API endpoints."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterType(Enum):
    """Parameter types for API endpoints."""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    BODY = "body"
    FORM = "form"


@dataclass
class APIParameter:
    """API parameter definition."""
    name: str
    type: str
    location: ParameterType
    description: str
    required: bool = True
    default: Any = None
    example: Any = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIResponse:
    """API response definition."""
    status_code: int
    description: str
    schema: Dict[str, Any]
    example: Any = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class APIEndpoint:
    """Complete API endpoint documentation."""
    path: str
    method: HTTPMethod
    summary: str
    description: str
    tags: List[str]
    parameters: List[APIParameter] = field(default_factory=list)
    responses: List[APIResponse] = field(default_factory=list)
    authentication_required: bool = True
    rate_limits: Dict[str, int] = field(default_factory=dict)
    deprecated: bool = False
    version: str = "1.0"
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class APITestCase:
    """API test case definition."""
    test_id: str
    endpoint: APIEndpoint
    test_name: str
    description: str
    request_data: Dict[str, Any]
    expected_responses: List[int]  # Expected status codes
    setup_data: Optional[Dict[str, Any]] = None
    cleanup_data: Optional[Dict[str, Any]] = None
    assertions: List[Dict[str, Any]] = field(default_factory=list)


class APIDocumentationGenerator:
    """Generate comprehensive API documentation."""
    
    def __init__(self):
        self.endpoints: Dict[str, APIEndpoint] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.security_schemes: Dict[str, Dict[str, Any]] = {}
        
    def register_endpoint(self, endpoint: APIEndpoint):
        """Register an API endpoint."""
        key = f"{endpoint.method.value}:{endpoint.path}"
        self.endpoints[key] = endpoint
        
    def add_schema(self, name: str, schema: Dict[str, Any]):
        """Add a reusable schema definition."""
        self.schemas[name] = schema
        
    def add_security_scheme(self, name: str, scheme: Dict[str, Any]):
        """Add a security scheme definition."""
        self.security_schemes[name] = scheme
        
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification."""
        
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "AI Customer Service Assistant API",
                "description": "Comprehensive API for AI-powered customer service system",
                "version": "1.0.0",
                "contact": {
                    "name": "API Support",
                    "email": "api-support@example.com"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                },
                {
                    "url": "https://api.example.com",
                    "description": "Production server"
                }
            ],
            "security": [
                {"bearerAuth": []}
            ],
            "components": {
                "schemas": self.schemas,
                "securitySchemes": self.security_schemes
            },
            "paths": {},
            "tags": self._generate_tags()
        }
        
        # Generate paths
        for endpoint in self.endpoints.values():
            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}
                
            method_spec = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "parameters": self._format_parameters(endpoint.parameters),
                "responses": self._format_responses(endpoint.responses),
                "security": [] if not endpoint.authentication_required else None
            }
            
            if endpoint.deprecated:
                method_spec["deprecated"] = True
                
            # Add request body for POST/PUT/PATCH
            if endpoint.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]:
                body_params = [p for p in endpoint.parameters if p.location == ParameterType.BODY]
                if body_params:
                    method_spec["requestBody"] = self._format_request_body(body_params[0])
            
            spec["paths"][endpoint.path][endpoint.method.value.lower()] = method_spec
            
        return spec
    
    def _generate_tags(self) -> List[Dict[str, str]]:
        """Generate tag definitions."""
        all_tags = set()
        for endpoint in self.endpoints.values():
            all_tags.update(endpoint.tags)
            
        tag_descriptions = {
            "authentication": "User authentication and authorization",
            "chat": "Chat and conversation management",
            "users": "User management operations",
            "analytics": "Analytics and reporting",
            "admin": "Administrative operations",
            "health": "System health and monitoring"
        }
        
        return [
            {
                "name": tag,
                "description": tag_descriptions.get(tag, f"Operations related to {tag}")
            }
            for tag in sorted(all_tags)
        ]
    
    def _format_parameters(self, parameters: List[APIParameter]) -> List[Dict[str, Any]]:
        """Format parameters for OpenAPI spec."""
        formatted = []
        
        for param in parameters:
            if param.location == ParameterType.BODY:
                continue  # Handle separately as requestBody
                
            param_spec = {
                "name": param.name,
                "in": param.location.value,
                "description": param.description,
                "required": param.required,
                "schema": {"type": param.type}
            }
            
            if param.example is not None:
                param_spec["example"] = param.example
                
            if param.default is not None:
                param_spec["schema"]["default"] = param.default
                
            formatted.append(param_spec)
            
        return formatted
    
    def _format_responses(self, responses: List[APIResponse]) -> Dict[str, Dict[str, Any]]:
        """Format responses for OpenAPI spec."""
        formatted = {}
        
        for response in responses:
            response_spec = {
                "description": response.description,
                "content": {
                    "application/json": {
                        "schema": response.schema
                    }
                }
            }
            
            if response.example is not None:
                response_spec["content"]["application/json"]["example"] = response.example
                
            if response.headers:
                response_spec["headers"] = {
                    name: {"description": desc, "schema": {"type": "string"}}
                    for name, desc in response.headers.items()
                }
                
            formatted[str(response.status_code)] = response_spec
            
        return formatted
    
    def _format_request_body(self, body_param: APIParameter) -> Dict[str, Any]:
        """Format request body for OpenAPI spec."""
        return {
            "description": body_param.description,
            "required": body_param.required,
            "content": {
                "application/json": {
                    "schema": {"type": body_param.type}
                }
            }
        }
    
    def generate_markdown_docs(self) -> str:
        """Generate markdown documentation."""
        docs = ["# AI Customer Service Assistant API Documentation\n"]
        
        # Group endpoints by tags
        endpoints_by_tag = {}
        for endpoint in self.endpoints.values():
            for tag in endpoint.tags:
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                endpoints_by_tag[tag].append(endpoint)
        
        for tag, endpoints in sorted(endpoints_by_tag.items()):
            docs.append(f"## {tag.title()}\n")
            
            for endpoint in sorted(endpoints, key=lambda x: x.path):
                docs.append(f"### {endpoint.method.value} {endpoint.path}\n")
                docs.append(f"{endpoint.description}\n")
                
                if endpoint.parameters:
                    docs.append("#### Parameters\n")
                    docs.append("| Name | Type | Location | Required | Description |")
                    docs.append("|------|------|----------|----------|-------------|")
                    
                    for param in endpoint.parameters:
                        required = "Yes" if param.required else "No"
                        docs.append(f"| {param.name} | {param.type} | {param.location.value} | {required} | {param.description} |")
                    
                    docs.append("")
                
                if endpoint.responses:
                    docs.append("#### Responses\n")
                    docs.append("| Status Code | Description |")
                    docs.append("|-------------|-------------|")
                    
                    for response in endpoint.responses:
                        docs.append(f"| {response.status_code} | {response.description} |")
                    
                    docs.append("")
                
                if endpoint.examples:
                    docs.append("#### Examples\n")
                    for i, example in enumerate(endpoint.examples, 1):
                        docs.append(f"##### Example {i}\n")
                        docs.append("```json")
                        docs.append(json.dumps(example, indent=2))
                        docs.append("```\n")
                
                docs.append("---\n")
        
        return "\n".join(docs)


class APITestSuite:
    """Comprehensive API testing suite."""
    
    def __init__(self):
        self.test_cases: List[APITestCase] = []
        self.test_results: List[Dict[str, Any]] = []
        
    def add_test_case(self, test_case: APITestCase):
        """Add a test case to the suite."""
        self.test_cases.append(test_case)
        
    async def run_tests(self, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """Run all test cases."""
        results = {
            "total_tests": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "test_results": []
        }
        
        for test_case in self.test_cases:
            result = await self._run_single_test(test_case, base_url)
            results["test_results"].append(result)
            
            if result["status"] == "passed":
                results["passed"] += 1
            elif result["status"] == "failed":
                results["failed"] += 1
            else:
                results["skipped"] += 1
        
        return results
    
    async def _run_single_test(self, test_case: APITestCase, base_url: str) -> Dict[str, Any]:
        """Run a single test case."""
        start_time = time.time()
        
        result = {
            "test_id": test_case.test_id,
            "test_name": test_case.test_name,
            "status": "pending",
            "duration_ms": 0,
            "error_message": None,
            "response_data": None,
            "assertions_passed": 0,
            "assertions_failed": 0
        }
        
        try:
            # Setup
            if test_case.setup_data:
                await self._run_setup(test_case.setup_data, base_url)
            
            # Make request
            url = f"{base_url}{test_case.endpoint.path}"
            response_data = await self._make_request(
                test_case.endpoint.method,
                url,
                test_case.request_data
            )
            
            result["response_data"] = response_data
            
            # Check expected status codes
            if response_data["status_code"] not in test_case.expected_responses:
                result["status"] = "failed"
                result["error_message"] = f"Expected status {test_case.expected_responses}, got {response_data['status_code']}"
            else:
                result["status"] = "passed"
            
            # Run assertions
            for assertion in test_case.assertions:
                assertion_result = self._run_assertion(assertion, response_data)
                if assertion_result:
                    result["assertions_passed"] += 1
                else:
                    result["assertions_failed"] += 1
                    if result["status"] == "passed":
                        result["status"] = "failed"
                        result["error_message"] = f"Assertion failed: {assertion}"
            
            # Cleanup
            if test_case.cleanup_data:
                await self._run_cleanup(test_case.cleanup_data, base_url)
                
        except Exception as e:
            result["status"] = "failed"
            result["error_message"] = str(e)
        
        result["duration_ms"] = (time.time() - start_time) * 1000
        return result
    
    async def _make_request(
        self,
        method: HTTPMethod,
        url: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make HTTP request (simplified simulation)."""
        
        # This is a simplified simulation
        # In a real implementation, you would use httpx or aiohttp
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Simulate response based on endpoint
        if "auth" in url:
            if method == HTTPMethod.POST:
                return {
                    "status_code": 200,
                    "data": {"access_token": "test_token", "token_type": "bearer"},
                    "headers": {}
                }
        elif "chat" in url:
            if method == HTTPMethod.POST:
                return {
                    "status_code": 201,
                    "data": {"id": 1, "message": "Response generated", "timestamp": datetime.utcnow().isoformat()},
                    "headers": {}
                }
            elif method == HTTPMethod.GET:
                return {
                    "status_code": 200,
                    "data": {"conversations": [], "total": 0},
                    "headers": {}
                }
        
        return {
            "status_code": 404,
            "data": {"detail": "Not found"},
            "headers": {}
        }
    
    def _run_assertion(self, assertion: Dict[str, Any], response_data: Dict[str, Any]) -> bool:
        """Run a single assertion."""
        assertion_type = assertion.get("type")
        
        if assertion_type == "status_code":
            return response_data["status_code"] == assertion["value"]
        elif assertion_type == "response_contains":
            return assertion["value"] in str(response_data["data"])
        elif assertion_type == "response_schema":
            # Simplified schema validation
            required_fields = assertion.get("required_fields", [])
            response_fields = response_data["data"].keys() if isinstance(response_data["data"], dict) else []
            return all(field in response_fields for field in required_fields)
        
        return True
    
    async def _run_setup(self, setup_data: Dict[str, Any], base_url: str):
        """Run test setup."""
        # Implementation for test data setup
        pass
    
    async def _run_cleanup(self, cleanup_data: Dict[str, Any], base_url: str):
        """Run test cleanup."""
        # Implementation for test data cleanup
        pass


class APIPerformanceTester:
    """Performance testing for API endpoints."""
    
    def __init__(self):
        self.load_test_results: List[Dict[str, Any]] = []
        
    async def run_load_test(
        self,
        endpoint: APIEndpoint,
        base_url: str,
        concurrent_users: int = 10,
        duration_seconds: int = 60,
        ramp_up_seconds: int = 10
    ) -> Dict[str, Any]:
        """Run a load test on an endpoint."""
        
        results = {
            "endpoint": f"{endpoint.method.value} {endpoint.path}",
            "test_config": {
                "concurrent_users": concurrent_users,
                "duration_seconds": duration_seconds,
                "ramp_up_seconds": ramp_up_seconds
            },
            "metrics": {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "average_response_time": 0,
                "min_response_time": float('inf'),
                "max_response_time": 0,
                "requests_per_second": 0,
                "error_rate": 0
            },
            "response_time_percentiles": {},
            "errors": []
        }
        
        # Collect response times and errors
        response_times = []
        errors = []
        
        async def user_session():
            """Simulate a user session."""
            session_start = time.time()
            while time.time() - session_start < duration_seconds:
                request_start = time.time()
                try:
                    # Simulate request
                    await asyncio.sleep(0.1 + (hash(str(time.time())) % 100) / 1000)  # Variable response time
                    response_time = (time.time() - request_start) * 1000
                    response_times.append(response_time)
                    
                    # Simulate occasional errors
                    if hash(str(time.time())) % 20 == 0:  # 5% error rate
                        errors.append("Simulated error")
                        
                except Exception as e:
                    errors.append(str(e))
                
                # Wait before next request
                await asyncio.sleep(1.0)
        
        # Start users gradually
        tasks = []
        for i in range(concurrent_users):
            await asyncio.sleep(ramp_up_seconds / concurrent_users)
            task = asyncio.create_task(user_session())
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate metrics
        if response_times:
            results["metrics"]["total_requests"] = len(response_times) + len(errors)
            results["metrics"]["successful_requests"] = len(response_times)
            results["metrics"]["failed_requests"] = len(errors)
            results["metrics"]["average_response_time"] = sum(response_times) / len(response_times)
            results["metrics"]["min_response_time"] = min(response_times)
            results["metrics"]["max_response_time"] = max(response_times)
            results["metrics"]["requests_per_second"] = len(response_times) / duration_seconds
            results["metrics"]["error_rate"] = len(errors) / (len(response_times) + len(errors))
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            results["response_time_percentiles"] = {
                "50th": sorted_times[int(len(sorted_times) * 0.5)],
                "90th": sorted_times[int(len(sorted_times) * 0.9)],
                "95th": sorted_times[int(len(sorted_times) * 0.95)],
                "99th": sorted_times[int(len(sorted_times) * 0.99)]
            }
        
        results["errors"] = errors[:10]  # Keep first 10 errors
        
        return results


def create_sample_endpoints() -> List[APIEndpoint]:
    """Create sample endpoint definitions for documentation."""
    
    endpoints = [
        APIEndpoint(
            path="/api/v1/auth/login",
            method=HTTPMethod.POST,
            summary="User login",
            description="Authenticate user and return access token",
            tags=["authentication"],
            parameters=[
                APIParameter(
                    name="credentials",
                    type="object",
                    location=ParameterType.BODY,
                    description="User credentials",
                    example={"email": "user@example.com", "password": "password123"}
                )
            ],
            responses=[
                APIResponse(
                    status_code=200,
                    description="Successful authentication",
                    schema={"type": "object", "properties": {"access_token": {"type": "string"}, "token_type": {"type": "string"}}},
                    example={"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer"}
                ),
                APIResponse(
                    status_code=401,
                    description="Invalid credentials",
                    schema={"type": "object", "properties": {"detail": {"type": "string"}}},
                    example={"detail": "Invalid email or password"}
                )
            ],
            authentication_required=False
        ),
        
        APIEndpoint(
            path="/api/v1/chat/conversations",
            method=HTTPMethod.GET,
            summary="List conversations",
            description="Get all conversations for the authenticated user",
            tags=["chat"],
            parameters=[
                APIParameter(
                    name="limit",
                    type="integer",
                    location=ParameterType.QUERY,
                    description="Maximum number of conversations to return",
                    required=False,
                    default=20,
                    example=10
                ),
                APIParameter(
                    name="offset",
                    type="integer",
                    location=ParameterType.QUERY,
                    description="Number of conversations to skip",
                    required=False,
                    default=0,
                    example=0
                )
            ],
            responses=[
                APIResponse(
                    status_code=200,
                    description="List of conversations",
                    schema={
                        "type": "object",
                        "properties": {
                            "conversations": {"type": "array", "items": {"type": "object"}},
                            "total": {"type": "integer"}
                        }
                    }
                )
            ]
        ),
        
        APIEndpoint(
            path="/api/v1/chat/conversations",
            method=HTTPMethod.POST,
            summary="Create conversation",
            description="Start a new chat conversation",
            tags=["chat"],
            parameters=[
                APIParameter(
                    name="conversation_data",
                    type="object",
                    location=ParameterType.BODY,
                    description="Conversation initialization data",
                    example={"title": "Product Support", "initial_message": "I need help with my order"}
                )
            ],
            responses=[
                APIResponse(
                    status_code=201,
                    description="Conversation created successfully",
                    schema={"type": "object", "properties": {"id": {"type": "integer"}, "title": {"type": "string"}}}
                )
            ]
        )
    ]
    
    return endpoints


def create_sample_test_cases() -> List[APITestCase]:
    """Create sample test cases."""
    
    test_cases = [
        APITestCase(
            test_id=str(uuid.uuid4()),
            endpoint=create_sample_endpoints()[0],  # Login endpoint
            test_name="Successful login",
            description="Test successful user authentication",
            request_data={"email": "test@example.com", "password": "testpass123"},
            expected_responses=[200],
            assertions=[
                {"type": "response_contains", "value": "access_token"},
                {"type": "response_schema", "required_fields": ["access_token", "token_type"]}
            ]
        ),
        
        APITestCase(
            test_id=str(uuid.uuid4()),
            endpoint=create_sample_endpoints()[0],  # Login endpoint
            test_name="Failed login - invalid credentials",
            description="Test authentication failure with invalid credentials",
            request_data={"email": "test@example.com", "password": "wrongpassword"},
            expected_responses=[401],
            assertions=[
                {"type": "response_contains", "value": "Invalid"}
            ]
        )
    ]
    
    return test_cases


# Factory functions
def create_documentation_generator() -> APIDocumentationGenerator:
    """Create API documentation generator."""
    generator = APIDocumentationGenerator()
    
    # Add common schemas
    generator.add_schema("User", {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string", "format": "email"},
            "created_at": {"type": "string", "format": "date-time"}
        }
    })
    
    generator.add_schema("Conversation", {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
            "user_id": {"type": "integer"}
        }
    })
    
    # Add security schemes
    generator.add_security_scheme("bearerAuth", {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    })
    
    # Register sample endpoints
    for endpoint in create_sample_endpoints():
        generator.register_endpoint(endpoint)
    
    return generator


def create_test_suite() -> APITestSuite:
    """Create API test suite with sample tests."""
    suite = APITestSuite()
    
    for test_case in create_sample_test_cases():
        suite.add_test_case(test_case)
    
    return suite
