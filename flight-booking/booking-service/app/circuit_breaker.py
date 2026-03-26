import logging
import time
from enum import Enum
from threading import Lock
from typing import Callable, Any
from .config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered, allow limited requests
    """
    
    def __init__(
        self,
        failure_threshold: int = None,
        timeout: int = None,
        half_open_max_calls: int = None
    ):
        self.failure_threshold = failure_threshold or settings.circuit_breaker_failure_threshold
        self.timeout = timeout or settings.circuit_breaker_timeout
        self.half_open_max_calls = half_open_max_calls or settings.circuit_breaker_half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.lock = Lock()
        
        logger.info(
            f"Circuit Breaker initialized: "
            f"threshold={self.failure_threshold}, "
            f"timeout={self.timeout}s, "
            f"half_open_max={self.half_open_max_calls}"
        )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    logger.warning("Circuit breaker is OPEN, rejecting call")
                    raise CircuitBreakerError("Circuit breaker is OPEN - service unavailable")
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    logger.warning("Circuit breaker HALF_OPEN limit reached, rejecting call")
                    raise CircuitBreakerError("Circuit breaker is HALF_OPEN - limited calls exceeded")
                self.half_open_calls += 1
        
        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.timeout
    
    def _transition_to_half_open(self):
        """Transition from OPEN to HALF_OPEN"""
        logger.info("Circuit breaker: OPEN → HALF_OPEN")
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker: HALF_OPEN → CLOSED (success)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker: HALF_OPEN → OPEN (failure)")
                self.state = CircuitState.OPEN
                self.half_open_calls = 0
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    logger.warning(
                        f"Circuit breaker: CLOSED → OPEN "
                        f"(failures: {self.failure_count}/{self.failure_threshold})"
                    )
                    self.state = CircuitState.OPEN
    
    def get_state(self) -> str:
        """Get current circuit breaker state"""
        return self.state.value


# Global circuit breaker instance for Flight Service
flight_service_circuit_breaker = CircuitBreaker()
