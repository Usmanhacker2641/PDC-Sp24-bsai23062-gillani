"""
Circuit Breaker Pattern Implementation
Student: Muhammad Usman Gillani | bsai23062
"""

import time
import asyncio
from enum import Enum
from typing import Callable, Any


class CircuitState(Enum):
    CLOSED = "CLOSED"        # Normal operation, calls go through
    OPEN = "OPEN"            # Failures exceeded threshold, calls blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit breaker is OPEN and a call is attempted."""
    pass


class CircuitBreaker:
    """
    Circuit Breaker with three states: CLOSED → OPEN → HALF_OPEN → CLOSED
    
    - CLOSED:    Calls pass through normally. Failures are counted.
    - OPEN:      Calls are short-circuited immediately. Fallback is returned.
    - HALF_OPEN: One trial call is allowed. Success resets; failure re-opens.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        success_threshold: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        # Auto-transition from OPEN → HALF_OPEN after cooldown
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._last_failure_time >= self.cooldown_seconds
        ):
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def _on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._reset()
        else:
            self._failure_count = 0  # Reset on success in CLOSED state

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def _reset(self):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute `func` through the circuit breaker.
        Raises CircuitOpenError if the breaker is OPEN.
        """
        current_state = self.state  # triggers auto-transition check

        if current_state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit is OPEN. Service unavailable. "
                f"Retry after {self.cooldown_seconds}s cooldown."
            )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise exc

    def get_status(self) -> dict:
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "seconds_since_last_failure": (
                round(time.monotonic() - self._last_failure_time, 2)
                if self._last_failure_time
                else None
            ),
        }
