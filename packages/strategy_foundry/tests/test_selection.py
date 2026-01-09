import pytest

from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import Promoter


def test_promoter_handles_missing_scores():
    challenger = {"score": 12.0, "max_drawdown": 0.15, "sharpe": 1.2}
    champion = {"max_drawdown": 0.25, "sharpe": 1.0}

    assert Promoter.should_promote(challenger, champion) is True


def test_champion_store_persists_score(tmp_path, monkeypatch):
    tmp_dir = tmp_path / "champions"
    monkeypatch.setattr("packages.strategy_foundry.selection.champion_store.CHAMPION_DIR", tmp_dir)

    store = ChampionStore()
    metrics = {"sharpe": 1.5, "max_drawdown": 0.1}
    store.save_new_champion({"id": "abc123"}, metrics, "5m", "20260109_000000", 55.0)

    data = store.load_current()

    assert data["score"] == pytest.approx(55.0)
    assert data["metrics"]["score"] == pytest.approx(55.0)
