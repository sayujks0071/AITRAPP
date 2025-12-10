"""Unit tests for LeaderLock refresh semantics (no real Redis required)."""
import pytest

from packages.core.leader_lock import LeaderLock
from packages.core.metrics import leader_changes_total


class FakeRedis:
    """Minimal async Redis stub for testing LeaderLock."""

    def __init__(self):
        self.store = {}
        self.ttls = {}

    async def get(self, key):
        return self.store.get(key)

    async def ttl(self, key):
        return self.ttls.get(key, -1)

    async def delete(self, key):
        self.store.pop(key, None)
        self.ttls.pop(key, None)

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = int(ex)
        return True

    async def eval(self, script, numkeys, key, instance_id, ttl):
        # Mirror the behaviour of the Lua script in LeaderLock.refresh:
        # if GET key == instance_id then EXPIRE key ttl else return 0
        if self.store.get(key) == instance_id:
            self.ttls[key] = int(ttl)
            return 1
        return 0


def _counter_value(counter) -> float:
    samples = list(counter._samples())
    if not samples:
        return 0.0
    return samples[0].value


@pytest.mark.asyncio
async def test_refresh_keeps_leadership_when_value_matches():
    """refresh() should succeed and keep leadership when key still matches instance_id."""
    redis = FakeRedis()
    lock = LeaderLock(redis, key="trader:leader:test", ttl=30)

    acquired = await lock.acquire()
    assert acquired is True
    assert lock.is_leader is True

    ok = await lock.refresh()
    assert ok is True
    assert lock.is_leader is True


@pytest.mark.asyncio
async def test_refresh_detects_lost_leadership_and_increments_metric():
    """refresh() should detect stolen lock, drop leadership, and bump leader_changes_total."""
    redis = FakeRedis()
    lock = LeaderLock(redis, key="trader:leader:test", ttl=30)

    acquired = await lock.acquire()
    assert acquired is True
    assert lock.is_leader is True

    before = _counter_value(leader_changes_total)

    # Simulate another instance stealing the lock
    redis.store[lock.key] = "other-instance"

    ok = await lock.refresh()
    assert ok is False
    assert lock.is_leader is False

    after = _counter_value(leader_changes_total)
    assert after == before + 1

