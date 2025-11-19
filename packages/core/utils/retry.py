"""Retry utilities for error-proofing API calls and operations"""
import time
import structlog
from functools import wraps
from typing import Callable, Any, Optional, Type, Tuple

logger = structlog.get_logger(__name__)


def retry_api_call(
    retries: int = 3,
    delay: float = 2.0,
    backoff: float = 1.5,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_failure: Optional[Callable] = None
):
    """
    Decorator to retry API calls on failure with exponential backoff.
    
    Inspired by StatGeist's error-proofing pattern, enhanced for AITRAPP.
    
    Args:
        retries: Number of retry attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 2.0)
        backoff: Multiplier for delay (exponential backoff) (default: 1.5)
        exceptions: Tuple of exception types to catch (default: all exceptions)
        on_failure: Optional callback function to call on final failure
    
    Example:
        @retry_api_call(retries=5, delay=1.0)
        def fetch_data(self, token):
            return self.kite.historical_data(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(retries):
                try:
                    result = func(*args, **kwargs)
                    # Log success if it was a retry
                    if attempt > 0:
                        logger.info(
                            f"API call succeeded after retry",
                            function=func.__name__,
                            attempt=attempt + 1
                        )
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < retries - 1:
                        logger.warning(
                            f"API call failed, retrying",
                            function=func.__name__,
                            error=str(e),
                            error_type=type(e).__name__,
                            attempt=attempt + 1,
                            retries=retries,
                            retrying_in=current_delay
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # Final attempt failed
                        logger.error(
                            f"API call failed after all retries",
                            function=func.__name__,
                            error=str(e),
                            error_type=type(e).__name__,
                            total_attempts=retries
                        )
                        
                        # Call failure callback if provided
                        if on_failure:
                            try:
                                on_failure(func, e, args, kwargs)
                            except Exception as callback_error:
                                logger.error(
                                    "Failure callback raised exception",
                                    callback_error=str(callback_error)
                                )
            
            # If all retries failed, return None or re-raise
            # For critical operations, you might want to re-raise
            logger.critical(
                f"Failed to execute {func.__name__} after {retries} attempts",
                error=str(last_exception) if last_exception else "Unknown error"
            )
            return None
        
        return wrapper
    return decorator


def retry_with_circuit_breaker(
    max_failures: int = 5,
    reset_timeout: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator with circuit breaker pattern.
    
    Stops retrying after max_failures consecutive failures,
    then allows retries again after reset_timeout seconds.
    
    Args:
        max_failures: Maximum consecutive failures before opening circuit
        reset_timeout: Seconds to wait before allowing retries again
        exceptions: Exception types to catch
    """
    failure_count = 0
    last_failure_time = 0.0
    circuit_open = False
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal failure_count, last_failure_time, circuit_open
            
            # Check if circuit should be reset
            if circuit_open:
                if time.time() - last_failure_time > reset_timeout:
                    logger.info(
                        f"Circuit breaker reset for {func.__name__}",
                        reset_after=reset_timeout
                    )
                    circuit_open = False
                    failure_count = 0
                else:
                    logger.warning(
                        f"Circuit breaker open for {func.__name__}",
                        remaining_time=reset_timeout - (time.time() - last_failure_time)
                    )
                    raise Exception(f"Circuit breaker open for {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                # Success - reset failure count
                if failure_count > 0:
                    logger.info(
                        f"Circuit breaker: Success after failures",
                        function=func.__name__,
                        previous_failures=failure_count
                    )
                failure_count = 0
                return result
                
            except exceptions as e:
                failure_count += 1
                last_failure_time = time.time()
                
                if failure_count >= max_failures:
                    circuit_open = True
                    logger.critical(
                        f"Circuit breaker opened for {func.__name__}",
                        failures=failure_count,
                        reset_timeout=reset_timeout
                    )
                
                raise
        
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    default_return: Any = None,
    log_errors: bool = True,
    reraise: bool = False
) -> Any:
    """
    Safely execute a function, catching all exceptions.
    
    Useful for non-critical operations that shouldn't crash the system.
    
    Args:
        func: Function to execute
        default_return: Value to return on error
        log_errors: Whether to log errors
        reraise: Whether to re-raise exceptions (default: False)
    
    Returns:
        Function result or default_return on error
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(
                f"Safe execute failed",
                function=func.__name__ if hasattr(func, '__name__') else str(func),
                error=str(e),
                error_type=type(e).__name__
            )
        
        if reraise:
            raise
        
        return default_return

