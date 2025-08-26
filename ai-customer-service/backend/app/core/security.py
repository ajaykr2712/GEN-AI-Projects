"""
Advanced API Security and Rate Limiting System

This module provides comprehensive API security features including:
- Advanced rate limiting with different strategies
- IP-based and user-based throttling
- Security headers and protection
- Request validation and sanitization
- API key management
- Abuse detection and prevention
"""

import time
import hashlib
import ipaddress
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from app.core.config import settings

# Type alias for Redis client to avoid import issues
RedisClient = Any


class RateLimitStrategy(Enum):
    """Different rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class ThreatLevel(Enum):
    """Security threat levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    requests: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_allowance: int = 0
    key_prefix: str = "rate_limit"
    
    
@dataclass
class SecurityEvent:
    """Security event for monitoring and alerting."""
    event_type: str
    source_ip: str
    user_id: Optional[int]
    timestamp: datetime
    threat_level: ThreatLevel
    details: Dict[str, Any]
    action_taken: str


@dataclass
class ApiKeyInfo:
    """API key information and metadata."""
    key_id: str
    name: str
    user_id: int
    permissions: List[str]
    rate_limits: Dict[str, RateLimitRule]
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    allowed_ips: List[str] = field(default_factory=list)
    
    
class AdvancedRateLimiter:
    """Advanced rate limiting with multiple strategies."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.lua_scripts = self._load_lua_scripts()
    
    async def check_rate_limit(
        self,
        key: str,
        rule: RateLimitRule,
        request_cost: int = 1
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits."""
        
        if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window_check(key, rule, request_cost)
        elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_check(key, rule, request_cost)
        elif rule.strategy == RateLimitStrategy.LEAKY_BUCKET:
            return await self._leaky_bucket_check(key, rule, request_cost)
        else:  # FIXED_WINDOW
            return await self._fixed_window_check(key, rule, request_cost)
    
    async def _sliding_window_check(
        self,
        key: str,
        rule: RateLimitRule,
        request_cost: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window rate limiting implementation."""
        now = time.time()
        window_start = now - rule.window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiration
        pipe.expire(key, rule.window_seconds)
        
        results = pipe.execute()
        current_count = results[1]
        
        if current_count + request_cost <= rule.requests:
            return True, {
                "allowed": True,
                "count": current_count + request_cost,
                "limit": rule.requests,
                "reset_time": now + rule.window_seconds,
                "retry_after": None
            }
        else:
            # Remove the request we just added since it's not allowed
            self.redis.zrem(key, str(now))
            
            return False, {
                "allowed": False,
                "count": current_count,
                "limit": rule.requests,
                "reset_time": now + rule.window_seconds,
                "retry_after": rule.window_seconds
            }
    
    async def _token_bucket_check(
        self,
        key: str,
        rule: RateLimitRule,
        request_cost: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket rate limiting implementation."""
        bucket_key = f"{key}:bucket"
        now = time.time()
        
        # Get current bucket state
        bucket_data = self.redis.hmget(bucket_key, ["tokens", "last_refill"])
        
        current_tokens = float(bucket_data[0]) if bucket_data[0] else rule.requests
        last_refill = float(bucket_data[1]) if bucket_data[1] else now
        
        # Calculate tokens to add based on time elapsed
        time_passed = now - last_refill
        tokens_to_add = time_passed * (rule.requests / rule.window_seconds)
        current_tokens = min(rule.requests, current_tokens + tokens_to_add)
        
        if current_tokens >= request_cost:
            # Allow request and consume tokens
            current_tokens -= request_cost
            
            self.redis.hmset(bucket_key, {
                "tokens": current_tokens,
                "last_refill": now
            })
            self.redis.expire(bucket_key, rule.window_seconds * 2)
            
            return True, {
                "allowed": True,
                "tokens_remaining": current_tokens,
                "tokens_limit": rule.requests,
                "retry_after": None
            }
        else:
            # Update bucket state but don't consume tokens
            self.redis.hmset(bucket_key, {
                "tokens": current_tokens,
                "last_refill": now
            })
            
            retry_after = (request_cost - current_tokens) / (rule.requests / rule.window_seconds)
            
            return False, {
                "allowed": False,
                "tokens_remaining": current_tokens,
                "tokens_limit": rule.requests,
                "retry_after": retry_after
            }
    
    async def _leaky_bucket_check(
        self,
        key: str,
        rule: RateLimitRule,
        request_cost: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Leaky bucket rate limiting implementation."""
        bucket_key = f"{key}:leaky"
        now = time.time()
        
        # Get current bucket state
        bucket_data = self.redis.hmget(bucket_key, ["volume", "last_leak"])
        
        current_volume = float(bucket_data[0]) if bucket_data[0] else 0
        last_leak = float(bucket_data[1]) if bucket_data[1] else now
        
        # Calculate leak since last check
        time_passed = now - last_leak
        leak_amount = time_passed * (rule.requests / rule.window_seconds)
        current_volume = max(0, current_volume - leak_amount)
        
        if current_volume + request_cost <= rule.requests:
            # Allow request and add to bucket
            current_volume += request_cost
            
            self.redis.hmset(bucket_key, {
                "volume": current_volume,
                "last_leak": now
            })
            self.redis.expire(bucket_key, rule.window_seconds * 2)
            
            return True, {
                "allowed": True,
                "volume": current_volume,
                "capacity": rule.requests,
                "retry_after": None
            }
        else:
            # Update leak time but don't add volume
            self.redis.hmset(bucket_key, {
                "volume": current_volume,
                "last_leak": now
            })
            
            retry_after = (current_volume + request_cost - rule.requests) / (rule.requests / rule.window_seconds)
            
            return False, {
                "allowed": False,
                "volume": current_volume,
                "capacity": rule.requests,
                "retry_after": retry_after
            }
    
    async def _fixed_window_check(
        self,
        key: str,
        rule: RateLimitRule,
        request_cost: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window rate limiting implementation."""
        now = time.time()
        window_start = int(now // rule.window_seconds) * rule.window_seconds
        window_key = f"{key}:{window_start}"
        
        current_count = self.redis.get(window_key)
        current_count = int(current_count) if current_count else 0
        
        if current_count + request_cost <= rule.requests:
            # Allow request
            pipe = self.redis.pipeline()
            pipe.incr(window_key, request_cost)
            pipe.expire(window_key, rule.window_seconds)
            pipe.execute()
            
            return True, {
                "allowed": True,
                "count": current_count + request_cost,
                "limit": rule.requests,
                "window_start": window_start,
                "window_end": window_start + rule.window_seconds,
                "retry_after": None
            }
        else:
            retry_after = window_start + rule.window_seconds - now
            
            return False, {
                "allowed": False,
                "count": current_count,
                "limit": rule.requests,
                "window_start": window_start,
                "window_end": window_start + rule.window_seconds,
                "retry_after": retry_after
            }
    
    def _load_lua_scripts(self) -> Dict[str, Any]:
        """Load Lua scripts for atomic Redis operations."""
        return {
            "sliding_window": """
                local key = KEYS[1]
                local now = tonumber(ARGV[1])
                local window = tonumber(ARGV[2])
                local limit = tonumber(ARGV[3])
                local cost = tonumber(ARGV[4])
                
                redis.call('zremrangebyscore', key, 0, now - window)
                local current = redis.call('zcard', key)
                
                if current + cost <= limit then
                    redis.call('zadd', key, now, now)
                    redis.call('expire', key, window)
                    return {1, current + cost}
                else
                    return {0, current}
                end
            """
        }


class IPWhitelistManager:
    """Manage IP whitelisting and blacklisting."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.whitelist_key = "ip:whitelist"
        self.blacklist_key = "ip:blacklist"
        self.suspicious_key = "ip:suspicious"
    
    async def is_ip_allowed(self, ip_address: str) -> Tuple[bool, str]:
        """Check if IP address is allowed."""
        
        # Check blacklist first
        if self.redis.sismember(self.blacklist_key, ip_address):
            return False, "blacklisted"
        
        # Check if IP is in CIDR ranges
        for cidr in self._get_blacklisted_cidrs():
            if self._ip_in_cidr(ip_address, cidr):
                return False, "blacklisted_range"
        
        # Check suspicious activity
        suspicious_score = self._get_suspicious_score(ip_address)
        if suspicious_score > 0.8:  # 80% threshold
            return False, "suspicious_activity"
        
        return True, "allowed"
    
    async def add_to_blacklist(
        self,
        ip_address: str,
        reason: str,
        duration_seconds: Optional[int] = None
    ):
        """Add IP to blacklist."""
        self.redis.sadd(self.blacklist_key, ip_address)
        
        # Store reason and timestamp
        self.redis.hset(
            f"blacklist:details:{ip_address}",
            mapping={
                "reason": reason,
                "timestamp": time.time(),
                "duration": duration_seconds or 0
            }
        )
        
        if duration_seconds:
            self.redis.expire(f"blacklist:details:{ip_address}", duration_seconds)
    
    async def add_suspicious_activity(
        self,
        ip_address: str,
        activity_type: str,
        weight: float = 1.0
    ):
        """Record suspicious activity from IP."""
        key = f"{self.suspicious_key}:{ip_address}"
        
        # Add to sorted set with timestamp
        self.redis.zadd(key, {activity_type: time.time()})
        
        # Keep only last 24 hours of activity
        yesterday = time.time() - 86400
        self.redis.zremrangebyscore(key, 0, yesterday)
        
        # Set expiration
        self.redis.expire(key, 86400)
    
    def _get_suspicious_score(self, ip_address: str) -> float:
        """Calculate suspicious activity score for IP."""
        key = f"{self.suspicious_key}:{ip_address}"
        
        # Get recent activities (last hour)
        recent_threshold = time.time() - 3600
        recent_activities = self.redis.zrangebyscore(key, recent_threshold, "+inf")
        
        # Calculate score based on activity types and frequency
        score = 0.0
        activity_weights = {
            "failed_login": 0.2,
            "invalid_request": 0.1,
            "rate_limit_exceeded": 0.3,
            "suspicious_payload": 0.4,
            "scanner_behavior": 0.5
        }
        
        for activity in recent_activities:
            activity_type = activity.decode() if isinstance(activity, bytes) else activity
            score += activity_weights.get(activity_type, 0.1)
        
        return min(1.0, score)
    
    def _get_blacklisted_cidrs(self) -> List[str]:
        """Get blacklisted CIDR ranges."""
        # Common malicious IP ranges
        return [
            "10.0.0.0/8",      # Private networks shouldn't access public APIs
            "172.16.0.0/12",   # Private networks
            "192.168.0.0/16",  # Private networks (if this is a public service)
            # Add known malicious ranges here
        ]
    
    def _ip_in_cidr(self, ip_address: str, cidr: str) -> bool:
        """Check if IP address is in CIDR range."""
        try:
            return ipaddress.ip_address(ip_address) in ipaddress.ip_network(cidr)
        except ValueError:
            return False


class APIKeyManager:
    """Manage API keys and their permissions."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.keys_prefix = "api_keys"
    
    async def create_api_key(
        self,
        user_id: int,
        name: str,
        permissions: List[str],
        rate_limits: Optional[Dict[str, RateLimitRule]] = None,
        allowed_ips: Optional[List[str]] = None
    ) -> str:
        """Create a new API key."""
        
        # Generate secure key
        key_data = f"{user_id}:{name}:{time.time()}"
        api_key = hashlib.sha256(key_data.encode()).hexdigest()
        
        key_info = ApiKeyInfo(
            key_id=api_key[:8],
            name=name,
            user_id=user_id,
            permissions=permissions,
            rate_limits=rate_limits or {},
            created_at=datetime.utcnow(),
            allowed_ips=allowed_ips or []
        )
        
        # Store key info
        self.redis.hset(
            f"{self.keys_prefix}:{api_key}",
            mapping={
                "key_id": key_info.key_id,
                "name": key_info.name,
                "user_id": key_info.user_id,
                "permissions": ",".join(key_info.permissions),
                "created_at": key_info.created_at.isoformat(),
                "is_active": "true",
                "allowed_ips": ",".join(key_info.allowed_ips)
            }
        )
        
        return api_key
    
    async def validate_api_key(
        self,
        api_key: str,
        required_permission: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> Tuple[bool, Optional[ApiKeyInfo]]:
        """Validate API key and check permissions."""
        
        key_data = self.redis.hgetall(f"{self.keys_prefix}:{api_key}")
        if not key_data:
            return False, None
        
        # Check if key is active
        if key_data.get(b"is_active", b"false").decode() != "true":
            return False, None
        
        # Reconstruct key info
        key_info = ApiKeyInfo(
            key_id=key_data[b"key_id"].decode(),
            name=key_data[b"name"].decode(),
            user_id=int(key_data[b"user_id"]),
            permissions=key_data[b"permissions"].decode().split(","),
            rate_limits={},  # Would need to deserialize from Redis
            created_at=datetime.fromisoformat(key_data[b"created_at"].decode()),
            allowed_ips=key_data.get(b"allowed_ips", b"").decode().split(",") if key_data.get(b"allowed_ips") else []
        )
        
        # Check permissions
        if required_permission and required_permission not in key_info.permissions:
            return False, key_info
        
        # Check IP restrictions
        if client_ip and key_info.allowed_ips:
            if client_ip not in key_info.allowed_ips:
                ip_allowed = False
                for allowed_ip in key_info.allowed_ips:
                    if "/" in allowed_ip:  # CIDR notation
                        try:
                            if ipaddress.ip_address(client_ip) in ipaddress.ip_network(allowed_ip):
                                ip_allowed = True
                                break
                        except ValueError:
                            continue
                
                if not ip_allowed:
                    return False, key_info
        
        # Update last used timestamp
        self.redis.hset(f"{self.keys_prefix}:{api_key}", "last_used", datetime.utcnow().isoformat())
        
        return True, key_info
    
    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        key_exists = self.redis.exists(f"{self.keys_prefix}:{api_key}")
        if key_exists:
            self.redis.hset(f"{self.keys_prefix}:{api_key}", "is_active", "false")
            return True
        return False


class SecurityMonitor:
    """Monitor and respond to security threats."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.events_key = "security:events"
        self.ip_manager = IPWhitelistManager(redis_client)
    
    async def record_security_event(self, event: SecurityEvent):
        """Record a security event."""
        event_data = {
            "event_type": event.event_type,
            "source_ip": event.source_ip,
            "user_id": event.user_id,
            "timestamp": event.timestamp.isoformat(),
            "threat_level": event.threat_level.value,
            "details": str(event.details),
            "action_taken": event.action_taken
        }
        
        # Store in time-series format
        self.redis.zadd(self.events_key, {
            f"{event.timestamp.timestamp()}:{event.source_ip}": event.timestamp.timestamp()
        })
        
        # Store detailed event data
        self.redis.hset(
            f"security:event:{event.timestamp.timestamp()}:{event.source_ip}",
            mapping=event_data
        )
        
        # Auto-response based on threat level
        await self._auto_respond(event)
    
    async def _auto_respond(self, event: SecurityEvent):
        """Automatically respond to security threats."""
        
        if event.threat_level == ThreatLevel.HIGH:
            # Temporarily blacklist IP for 1 hour
            await self.ip_manager.add_to_blacklist(
                event.source_ip,
                f"Auto-blocked due to {event.event_type}",
                duration_seconds=3600
            )
        
        elif event.threat_level == ThreatLevel.CRITICAL:
            # Blacklist IP for 24 hours
            await self.ip_manager.add_to_blacklist(
                event.source_ip,
                f"Auto-blocked due to {event.event_type}",
                duration_seconds=86400
            )
        
        # Record suspicious activity
        await self.ip_manager.add_suspicious_activity(
            event.source_ip,
            event.event_type,
            weight=self._get_threat_weight(event.threat_level)
        )
    
    def _get_threat_weight(self, threat_level: ThreatLevel) -> float:
        """Get weight for threat level."""
        weights = {
            ThreatLevel.LOW: 0.1,
            ThreatLevel.MEDIUM: 0.3,
            ThreatLevel.HIGH: 0.6,
            ThreatLevel.CRITICAL: 1.0
        }
        return weights.get(threat_level, 0.1)


# Security Headers Middleware
class SecurityHeaders:
    """Security headers for API responses."""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get standard security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }


# Factory functions
async def create_rate_limiter() -> AdvancedRateLimiter:
    """Create rate limiter instance."""
    redis_client = redis.from_url(settings.REDIS_URL)
    return AdvancedRateLimiter(redis_client)


async def create_security_monitor() -> SecurityMonitor:
    """Create security monitor instance."""
    redis_client = redis.from_url(settings.REDIS_URL)
    return SecurityMonitor(redis_client)


async def create_api_key_manager() -> APIKeyManager:
    """Create API key manager instance."""
    redis_client = redis.from_url(settings.REDIS_URL)
    return APIKeyManager(redis_client)
