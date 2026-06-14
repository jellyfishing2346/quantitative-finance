# Contributing

This guide explains how to extend the framework — primarily by adding new trading strategies, but also by adding metrics, data sources, or dashboard controls.

---

## Development Setup

```bash
git clone https://github.com/faizanakhan2003/quantitative-finance.git
cd quantitative-finance

# Python 3.11 required
pyenv shell 3.11.15
python -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt
```

Run the test suite to confirm the baseline:

```bash
python -m pytest tests/ -v
# should show 53 passed
```

---

## Adding a New Strategy

### Step 1 — Write the strategy class

Create `quant_trading/strategies/my_strategy.py`:

```python
import backtrader as bt
from .base import BaseStrategy


class MyStrategy(BaseStrategy):
    params = (
        ("my_param", 14),      # declare all tunable parameters here
    )

    def __init__(self):
        super().__init__()
        # declare Backtrader indicators
        self.rsi = bt.ind.RSI(period=self.params.my_param)

    def next(self):
        if self.rsi[0] < 30 and not self.position:
            self.buy(size=self._get_size(self.data.close[0]))
        elif self.rsi[0] > 70 and self.position:
            self.close()
```

**Rules:**
- Always call `super().__init__()` — it sets up sizing and logging
- Always check `self.position` before buying and after selling
- Use `self._get_size(price)` for position sizing — never hardcode share counts
- Only call `self.buy()` / `self.close()` — never `self.sell()` for a long-only strategy

### Step 2 — Add a signal function (optional but recommended)

Add a pure pandas version to `quant_trading/strategies/signals.py`:

```python
def rsi_signal(df: pd.DataFrame, period: int, oversold: float = 30, overbought: float = 70) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    signal = pd.Series(0, index=df.index)
    signal[rsi < oversold]  = 1
    signal[rsi > overbought] = -1
    return signal
```

### Step 3 — Export from `__init__.py`

Add to `quant_trading/strategies/__init__.py`:

```python
from .my_strategy import MyStrategy
```

### Step 4 — Wire into the dashboard

In `quant_trading/dashboard/callbacks.py`, add to `STRATEGY_MAP`:

```python
STRATEGY_MAP = {
    "DualMAMomentum": DualMAMomentum,
    "BollingerMeanReversion": BollingerMeanReversion,
    "MyStrategy": MyStrategy,            # add this
}
```

And handle params in `_build_params()`:

```python
def _build_params(strategy_name, fast, slow):
    if strategy_name == "MyStrategy":
        return {"my_param": fast}        # map slider to param
    ...
```

Add the strategy name to `STRATEGIES` in `layout.py`:

```python
STRATEGIES = ["DualMAMomentum", "BollingerMeanReversion", "MyStrategy"]
```

### Step 5 — Write tests

Add to `tests/test_strategies.py`:

```python
# Test the signal function
def test_rsi_signal_fires():
    from quant_trading.strategies.signals import rsi_signal
    df = make_ohlcv_df(100)
    sig = rsi_signal(df, period=14)
    assert isinstance(sig, pd.Series)

# Smoke test — confirm the strategy trades
def test_my_strategy_trades():
    df = make_ohlcv_df(200)
    strat, final_value = run_strategy(MyStrategy, df, my_param=14)
    assert final_value != 100_000
```

---

## Adding a New Metric

Add a function to `quant_trading/analytics/metrics.py`:

```python
def calmar_ratio(returns: pd.Series) -> float:
    mdd = max_drawdown(returns)
    if mdd == 0:
        return float("inf")
    return annualised_return(returns) / abs(mdd)
```

Then export it from `quant_trading/analytics/__init__.py` and add it to `BacktestResult.compute_metrics()` in `results.py`.

---

## Adding a New Data Source

Implement `_fetch_mysource()` in `quant_trading/data/fetcher.py` following the same pattern as `_fetch_yfinance()` — return a normalised DataFrame with columns `open, high, low, close, volume` and a `DatetimeIndex` named `timestamp`.

Then add it to the `_fetch_live()` fallback chain.

---

## Code Style

- No comments that describe *what* the code does — names should do that
- Comments only for non-obvious *why* (a constraint, workaround, or subtle invariant)
- No docstrings on internal functions
- Type hints on all public function signatures
- Tests use synthetic data — never real network calls
- One test per behaviour — not one test per function

---

## Running Tests

```bash
# all tests
python -m pytest tests/ -v

# single file
python -m pytest tests/test_strategies.py -v

# with coverage
python -m pytest tests/ --cov=quant_trading --cov-report=term-missing
```

All 53 tests must pass before submitting a pull request.
