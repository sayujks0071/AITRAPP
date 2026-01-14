class SanityCheck:
    def __init__(self, min_trades=30, max_dd_pct=35.0):
        self.min_trades = min_trades
        self.max_dd_pct = max_dd_pct

    def check(self, metrics: dict) -> tuple[bool, str]:
        if metrics.get('trades', 0) < self.min_trades:
            return False, f"Not enough trades: {metrics.get('trades', 0)} < {self.min_trades}"

        if abs(metrics.get('max_dd', 0)) * 100 > self.max_dd_pct:
             return False, f"Max DD too high: {metrics.get('max_dd', 0)*100:.1f}% > {self.max_dd_pct}%"

        if metrics.get('cagr', 0) <= 0:
            return False, "Negative CAGR"

        return True, "OK"
