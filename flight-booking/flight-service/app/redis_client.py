import json
import logging
from typing import Optional, List
from redis.sentinel import Sentinel
from .config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self):
        self.sentinel = None
        self.master = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Redis Sentinel connection"""
        try:
            # Parse sentinel addresses
            sentinel_list = []
            for addr in settings.redis_sentinels.split(','):
                host, port = addr.strip().split(':')
                sentinel_list.append((host, int(port)))
            
            logger.info(f"Connecting to Redis Sentinel: {sentinel_list}")
            
            # Create Sentinel instance
            self.sentinel = Sentinel(
                sentinel_list,
                socket_timeout=0.5,
                password=settings.redis_password if settings.redis_password else None
            )
            
            # Get master connection
            self.master = self.sentinel.master_for(
                settings.redis_master_name,
                socket_timeout=0.5,
                password=settings.redis_password if settings.redis_password else None
            )
            
            # Test connection
            self.master.ping()
            logger.info("Successfully connected to Redis master")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.master = None
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.master:
            logger.warning("Redis not available, cache miss")
            return None
        
        try:
            value = self.master.get(key)
            if value:
                logger.info(f"Cache HIT: {key}")
                return value.decode('utf-8')
            else:
                logger.info(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int):
        """Set value in cache with TTL"""
        if not self.master:
            logger.warning("Redis not available, skipping cache set")
            return
        
        try:
            self.master.setex(key, ttl, value)
            logger.info(f"Cache SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
    
    def delete(self, key: str):
        """Delete key from cache"""
        if not self.master:
            return
        
        try:
            self.master.delete(key)
            logger.info(f"Cache DELETE: {key}")
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
    
    def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.master:
            return
        
        try:
            keys = self.master.keys(pattern)
            if keys:
                self.master.delete(*keys)
                logger.info(f"Cache DELETE pattern: {pattern} ({len(keys)} keys)")
        except Exception as e:
            logger.error(f"Redis DELETE pattern error for {pattern}: {e}")


# Global cache instance
cache = RedisCache()
