"""Kite Client wrapper for order operations"""
from typing import Optional, Callable
import structlog
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException, NetworkException

from packages.core.metrics import retries_total
from packages.core.utils.retry import retry_api_call

logger = structlog.get_logger(__name__)


class TokenExpiredError(Exception):
    """Raised when access token has expired"""
    pass


class KiteClient:
    """Wrapper around KiteConnect for order operations with token expiry handling"""
    
    def __init__(self, kite: KiteConnect, token_refresh_callback: Optional[Callable] = None):
        self.kite = kite
        self.token_refresh_callback = token_refresh_callback
    
    def _handle_auth_error(self, e: Exception) -> None:
        """Handle authentication errors (401/403)"""
        error_str = str(e).lower()
        if '401' in error_str or '403' in error_str or 'token' in error_str or 'unauthorized' in error_str:
            logger.critical("Access token expired or invalid", error=str(e))
            retries_total.labels(type="token_refresh").inc()
            
            if self.token_refresh_callback:
                try:
                    self.token_refresh_callback()
                    logger.info("Token refreshed via callback")
                except Exception as refresh_error:
                    logger.error("Token refresh failed", error=str(refresh_error))
                    raise TokenExpiredError("Token expired and refresh failed")
            else:
                raise TokenExpiredError("Token expired - no refresh callback configured")
    
    @retry_api_call(retries=3, delay=1.0, exceptions=(NetworkException,))
    def place_order(self, **kwargs) -> Optional[str]:
        """
        Place an order via Kite Connect with token expiry handling and retries.
        
        Uses retry decorator for network errors, with special handling for token expiry.
        """
        try:
            order_id = self.kite.place_order(**kwargs)
            logger.info("Order placed", order_id=order_id, **kwargs)
            return str(order_id)
        except (TokenException,) as e:
            # Token errors: handle auth and retry once (not via decorator)
            self._handle_auth_error(e)
            try:
                order_id = self.kite.place_order(**kwargs)
                logger.info("Order placed after token refresh", order_id=order_id, **kwargs)
                return str(order_id)
            except Exception as retry_error:
                logger.error("Failed to place order after token refresh", error=str(retry_error), **kwargs)
                raise
        except NetworkException as e:
            # Network errors: let retry decorator handle
            logger.warning("Network error in place_order, will retry", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to place order", error=str(e), **kwargs)
            raise
    
    @retry_api_call(retries=3, delay=1.0, exceptions=(NetworkException,))
    def cancel_order(self, order_id: str, variety: str = "regular") -> None:
        """Cancel an order with retry on network errors"""
        try:
            self.kite.cancel_order(variety=variety, order_id=order_id)
            logger.info("Order cancelled", order_id=order_id)
        except (TokenException,) as e:
            self._handle_auth_error(e)
            # Retry once after token refresh
            self.kite.cancel_order(variety=variety, order_id=order_id)
            logger.info("Order cancelled after token refresh", order_id=order_id)
        except NetworkException as e:
            logger.warning("Network error in cancel_order, will retry", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to cancel order", error=str(e), order_id=order_id)
            raise
    
    @retry_api_call(retries=3, delay=1.0, exceptions=(NetworkException,))
    def get_orders(self) -> list:
        """Get all orders with retry on network errors"""
        try:
            orders = self.kite.orders()
            return orders
        except (TokenException,) as e:
            self._handle_auth_error(e)
            # Retry once after token refresh
            return self.kite.orders()
        except NetworkException as e:
            logger.warning("Network error in get_orders, will retry", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to get orders", error=str(e))
            return []

