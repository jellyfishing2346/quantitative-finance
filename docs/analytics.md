# Analytics

The analytics layer computes performance metrics from an equity curve — the time series of portfolio value produced by a backtest. All functions are stateless and take a `pd.Series` of daily returns.

---

## Metric Reference

### Annualised Return

The compound annual growth rate (CAGR) of the strategy — what constant yearly return would produce the same total growth.

```
annualised_return = (total_growth) ^ (1 / n_years) - 1

where total_growth = product of (1 + daily_return) for all bars
      n_years = number of bars / 252
```

```python
from quant_trading.analytics import annualised_return

r = result.equity_curve["returns"].dropna()
print(f"{annualised_return(r):.2%}")   # e.g. 14.23%
```

A positive value means the strategy grew capital. A negative value means it lost capital, compounded.

---

### Annualised Volatility

The standard deviation of daily returns, scaled to an annual figure. Measures how much the strategy's returns vary day to day.

```
annualised_volatility = daily_std × sqrt(252)
```

Higher volatility means larger swings — both up and down. A strategy with 30% annualised volatility should expect daily moves of roughly ±1.9% (30% / sqrt(252)).

---

### Sharpe Ratio

The most widely used risk-adjusted return metric. Measures return per unit of total risk.

```
sharpe = (mean_excess_return / std_excess_return) × sqrt(252)

where excess_return = daily_return - (risk_free_rate / 252)
```

```python
from quant_trading.analytics import sharpe_ratio

s = sharpe_ratio(r, risk_free=0.05)   # 5% annual risk-free rate
```

**Interpreting Sharpe:**

| Sharpe | Interpretation |
|--------|---------------|
| < 0 | Strategy loses money relative to risk-free rate |
| 0–0.5 | Poor |
| 0.5–1.0 | Acceptable |
| 1.0–2.0 | Good |
| > 2.0 | Excellent (rare in live trading) |

The risk-free rate defaults to 0.0, which is appropriate for backtests that don't model cash returns.

---

### Sortino Ratio

Like Sharpe, but only penalises *downside* volatility. The argument: investors don't mind upside variance — only losing money feels like risk.

```
sortino = (mean_excess_return / downside_std) × sqrt(252)

where downside_std = std of excess returns that are negative
```

A Sortino ratio significantly higher than the Sharpe ratio indicates the strategy has asymmetric returns — more upside volatility than downside, which is desirable.

---

### Maximum Drawdown

The largest peak-to-trough decline in portfolio value during the backtest period. Measures the worst-case loss an investor would have experienced.

```
drawdown(t) = (equity(t) - peak_equity_up_to_t) / peak_equity_up_to_t
max_drawdown = min(drawdown) across all t
```

```python
from quant_trading.analytics import max_drawdown

mdd = max_drawdown(r)   # e.g. -0.213 = 21.3% peak-to-trough loss
```

A 50% drawdown requires a 100% gain just to break even. This is why max drawdown matters more than it might appear.

---

### Win Rate

The fraction of completed trades that were profitable.

```
win_rate = winning_trades / total_trades
```

```python
from quant_trading.analytics import win_rate

pnls = [150, -80, 200, -30, 90, -45]   # list of per-trade P&L
print(win_rate(pnls))   # 0.5 = 50%
```

Win rate alone is not sufficient — a strategy with 30% win rate can be highly profitable if wins are much larger than losses (see profit factor).

---

### Profit Factor

Ratio of gross profit to gross loss across all trades. Values above 1.0 mean the strategy makes more than it loses in total.

```
profit_factor = sum(positive P&Ls) / abs(sum(negative P&Ls))
```

| Profit Factor | Interpretation |
|--------------|---------------|
| < 1.0 | Loses money overall |
| 1.0–1.5 | Marginal |
| 1.5–2.5 | Good |
| > 2.5 | Excellent |

---

## Using `compute_metrics()`

The most convenient way to get all metrics at once from a `BacktestResult`:

```python
result = runner.run(DualMAMomentum, df, params={"fast_period": 20, "slow_period": 50})
metrics = result.compute_metrics()

print(f"Annualised return:  {metrics['annualised_return']:.2%}")
print(f"Annualised vol:     {metrics['annualised_vol']:.2%}")
print(f"Sharpe ratio:       {metrics['sharpe']:.3f}")
print(f"Sortino ratio:      {metrics['sortino']:.3f}")
print(f"Max drawdown:       {metrics['max_drawdown']:.2%}")
```

---

## QuantStats Tearsheet

For a full institutional-grade report (HTML), use the tearsheet wrapper:

```python
from quant_trading.analytics import generate_tearsheet

returns = result.equity_curve["returns"].dropna()
generate_tearsheet(returns, output_path="report.html", title="AAPL DualMAMomentum")
```

Open `report.html` in a browser. The tearsheet includes:
- Monthly returns heatmap
- Rolling Sharpe ratio
- Drawdown periods table
- Distribution of returns
- Comparative statistics vs benchmark

To print a text summary instead:

```python
from quant_trading.analytics import print_stats

print_stats(returns)
```

---

## Equity Curve

The equity curve is extracted from Backtrader's `TimeReturn` analyzer and stored on `BacktestResult.equity_curve` as a DataFrame with two columns:

| Column | Description |
|--------|-------------|
| `equity` | Absolute portfolio value in dollars |
| `returns` | Period return (e.g. `0.012` = 1.2% gain that day) |

```python
ec = result.equity_curve
print(ec.head())

#             equity   returns
# 2022-01-03  100000   0.0000
# 2022-01-04  101200   0.0120
# 2022-01-05   99800  -0.0138
```

The index is a `DatetimeIndex` aligned to trading days in the backtest window.
