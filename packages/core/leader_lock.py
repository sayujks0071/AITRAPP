"""Leader lock to ensure only one orchestrator instance runs"""
import time
import uuid
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class LeaderLock:
    """Redis-based leader lock to prevent multiple orchestrator instances"""
    
    def __init__(self, redis, key: str = "trader:leader", ttl: int = 30):
        """
        Args:
            redis: Redis client (aioredis or redis)
            key: Redis key for leader lock
            ttl: Time-to-live in seconds (lock expires if not refreshed)
        """
        self.redis = redis
        self.key = key
        self.ttl = ttl
        self.instance_id = str(uuid.uuid4())
        self.is_leader = False
    
    async def acquire(self, retries: int = 3, retry_delay: float = 0.5) -> bool:
        """
        Try to acquire leader lock with retries.
        
        Args:
            retries: Number of retry attempts
            retry_delay: Delay between retries in seconds
        
        Returns:
            True if lock acquired, False if another instance is leader
        """
        import asyncio
        
        for attempt in range(retries):
            try:
                # First, check if lock exists and is stale (expired)
                existing = await self.redis.get(self.key)
                if existing:
                    # Lock exists - check if it's actually valid
                    # (Redis might return expired keys in some cases)
                    ttl = await self.redis.ttl(self.key)
                    if ttl > 0:
                        # Lock is still valid, another instance has it
                        existing_leader = existing
                        if isinstance(existing_leader, bytes):
                            existing_leader = existing_leader.decode()
                        logger.warning(
                            "Failed to acquire leader lock - another instance is leader",
                            instance_id=self.instance_id,
                            existing_leader=existing_leader,
                            attempt=attempt + 1,
                            retries=retries
                        )
                        if attempt < retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        return False
                    else:
                        # Lock expired, delete it and try again
                        logger.info("Leader lock expired, clearing and retrying", attempt=attempt + 1)
                        await self.redis.delete(self.key)
                
                # SET key val NX EX ttl
                # NX = only set if not exists
                # EX = expire after ttl seconds
                result = await self.redis.set(
                    self.key,
                    self.instance_id,
                    nx=True,
                    ex=self.ttl
                )
                
                if result:
                    self.is_leader = True
                    logger.info("Leader lock acquired", instance_id=self.instance_id, attempt=attempt + 1)
                    return True
                else:
                    # Lock was set between our check and set (race condition)
                    if attempt < retries - 1:
                        logger.debug("Race condition: lock acquired by another instance, retrying", attempt=attempt + 1)
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        existing_leader = await self.redis.get(self.key)
                        if existing_leader:
                            if isinstance(existing_leader, bytes):
                                existing_leader = existing_leader.decode()
                        logger.warning(
                            "Failed to acquire leader lock after retries",
                            instance_id=self.instance_id,
                            existing_leader=existing_leader
                        )
                        return False
            except Exception as e:
                logger.error("Error acquiring leader lock", error=str(e), attempt=attempt + 1, retries=retries)
                if attempt < retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return False
        
        return False
    
    async def refresh(self) -> bool:
        """
        Refresh leader lock (must be called periodically).
        
        Returns:
            True if still leader, False if lost leadership
        """
        if not self.is_leader:
            return False
        
        try:
            # Atomically refresh TTL only if we still own the lock.
            #
            # This avoids race conditions between GET/EXPIRE and removes the
            # need for async pipeline/watch (which was previously mis‑used and
            # triggered \"coroutine 'Pipeline.watch' was never awaited\").
            refresh_script = """
            if redis.call('GET', KEYS[1]) == ARGV[1] then
                return redis.call('EXPIRE', KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            result = await self.redis.eval(
                refresh_script,
                1,
                self.key,
                self.instance_id,
                int(self.ttl),
            )
            if result:
                # TTL was refreshed, we are still the leader
                return True
            
            # Lock is no longer held by this instance
            self.is_leader = False
            logger.warning("Lost leader lock", instance_id=self.instance_id)
            from packages.core.metrics import leader_changes_total
            leader_changes_total.inc()
            return False
        except Exception as e:
            logger.error("Error refreshing leader lock", error=str(e))
            self.is_leader = False
            return False
    
    async def release(self) -> None:
        """Release leader lock"""
        if not self.is_leader:
            return
        
        try:
            # Only delete if we're still the leader
            current_leader = await self.redis.get(self.key)
            # Handle both bytes and strings (Redis client compatibility)
            if current_leader:
                if isinstance(current_leader, bytes):
                    current_leader = current_leader.decode()
            if current_leader and current_leader == self.instance_id:
                await self.redis.delete(self.key)
                logger.info("Leader lock released", instance_id=self.instance_id)
            self.is_leader = False
        except Exception as e:
            logger.error("Error releasing leader lock", error=str(e))
