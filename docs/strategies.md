# Strategies

The strategy layer contains two production-ready trading strategies and a set of pure signal functions. Strategies are Backtrader `Strategy` subclasses; signal functions are plain pandas — testable without a backtest engine.

---

## How Strategies Work

Every strategy inherits from `BaseStrategy` and follows the same pattern:

```python
class MyStrategy(BaseStrategy):
    params = (("my_param", default_value),)

    def __init__(self):
        super().__init__()
        # declare indicators here — Backtrader computes them automatically

    def next(self):
        # called once per bar, after indicators have enough history
        # read indicator[0] for current value, [-1] for previous bar
        if buy_condition and not self.position:
            self.buy(size=self._get_size(self.data.close[0]))
        elif sell_condition and self.position:
            self.close()
```

---

## BaseStrategy

`quant_trading/strategies/base.py`

Provides two shared behaviours for all strategies:

### Position sizing — `_get_size(price)`

Uses a fixed-fractional approach: allocate `size_pct` of available cash per trade.

```
shares = floor((cash × size_pct) / price)
```

With default `size_pct=0.95`, a $100,000 portfolio buying at $150/share would purchase 633 shares, keeping 5% in reserve to cover commissions.

### Order logging — `notify_order(order)`

Called by Backtrader on every order status change. Logs fills and rejections at `INFO` and `WARNING` level respectively. This gives you a trade-by-trade audit trail in the application logs without any extra code in the strategy itself.

### Parameters

| Param | Default | Description |
|-------|---------|-------------|
| `size_pct` | `0.95` | Fraction of cash to deploy per trade |
| `stop_pct` | `None` | Hard stop-loss (e.g. `0.05` = 5% below entry). Not yet wired — reserved for a future release. |

---

## DualMAMomentum

`quant_trading/strategies/momentum.py`

**Type:** Trend-following / momentum

**Hypothesis:** When a fast-moving average crosses above a slow-moving average, momentum is positive and price is likely to continue rising.

### Signal logic

```
Fast SMA crosses ABOVE Slow SMA  →  BUY
Fast SMA crosses BELOW Slow SMA  →  CLOSE LONG
```

The crossover is detected with Backtrader's built-in `bt.ind.CrossOver`, which returns `+1` on the bar of an upward cross, `-1` on a downward cross, and `0` otherwise. This means signals fire on the exact bar the cross occurs — no look-ahead.

### Parameters

| Param | Default | Range (suggested) | Description |
|-------|---------|-------------------|-------------|
| `fast_period` | `20` | 5–50 | Lookback window for the fast SMA |
| `slow_period` | `50` | 20–200 | Lookback window for the slow SMA |
| `size_pct` | `0.95` | 0.5–1.0 | Position size as fraction of cash |

**Constraint:** `fast_period` must be strictly less than `slow_period`. Violating this produces undefined behaviour.

### Behaviour on typical market conditions

- **Trending markets:** performs well — captures extended moves
- **Choppy/ranging markets:** generates many false crossovers, leading to repeated small losses ("whipsaws")
- **High volatility:** the slow MA dampens noise, but extreme gaps can still cause adverse fills

### Pure signal function

```python
from quant_trading.strategies.signals import dual_ma_signal

signal = dual_ma_signal(df, fast=20, slow=50)
# returns pd.Series: +1 (fast > slow), -1 (fast < slow), 0 (equal or NaN)
```

---

## BollingerMeanReversion

`quant_trading/strategies/mean_reversion.py`

**Type:** Mean-reversion / counter-trend

**Hypothesis:** When price deviates significantly from its recent average (as measured by Bollinger Bands), it tends to revert back toward the mean.

### Signal logic

```
Z-score < -1.0  →  BUY   (price is below lower band — oversold)
Z-score >  0.0  →  CLOSE LONG  (price has reverted to mean)
```

The Z-score is computed as:

```
Z = (close - mid_band) / (top_band - mid_band)
```

Where `top_band - mid_band` equals one standard deviation. A Z-score of `-1.0` means price is exactly at the lower band; `-2.0` means it's one standard deviation below the lower band.

### Parameters

| Param | Default | Range (suggested) | Description |
|-------|---------|-------------------|-------------|
| `period` | `20` | 10–50 | Lookback for Bollinger Band calculation |
| `dev_factor` | `2.0` | 1.5–3.0 | Number of standard deviations for the bands |
| `size_pct` | `0.95` | 0.5–1.0 | Position size as fraction of cash |

### Behaviour on typical market conditions

- **Ranging markets:** performs well — price oscillates within bands and reverts reliably
- **Trending markets:** generates losing trades — price can "walk the band" indefinitely in a strong trend
- **High volatility regimes:** bands widen and signals become less frequent but more reliable

### Pure signal function

```python
from quant_trading.strategies.signals import bollinger_zscore

z = bollinger_zscore(df, period=20, dev=2.0)
# returns pd.Series of Z-scores, NaN for the first `period` bars
```

---

## Adding a New Strategy

1. Create `quant_trading/strategies/my_strategy.py`
2. Inherit from `BaseStrategy`
3. Declare params and indicators in `__init__`
4. Implement `next()` with buy/sell logic
5. Add imports to `quant_trading/strategies/__init__.py`
6. Add a corresponding entry in `callbacks.py`'s `STRATEGY_MAP` and `_build_params()`
7. Write a smoke test in `tests/test_strategies.py`

See [contributing.md](contributing.md) for a full walkthrough.

---

## Strategy Comparison

| Property | DualMAMomentum | BollingerMeanReversion |
|----------|---------------|----------------------|
| Signal type | Trend-following | Counter-trend |
| Works best in | Trending markets | Ranging markets |
| Trade frequency | Low (holds longer) | Higher (faster in/out) |
| Typical drawdown | Moderate | Low |
| Parameter sensitivity | Low | Medium |
