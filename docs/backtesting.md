# Backtesting

The backtest engine wraps Backtrader's cerebro in a clean Python interface, adds realistic transaction costs, and provides walk-forward splitting and parameter optimisation.

---

## BacktestRunner

`quant_trading/backtest/runner.py`

The central class. Accepts a strategy class and a DataFrame, runs the simulation, and returns a `BacktestResult`.

```python
from quant_trading.backtest import BacktestRunner
from quant_trading.strategies import DualMAMomentum

runner = BacktestRunner(
    commission=0.001,     # 0.1% per trade (both sides)
    slippage=0.0005,      # 0.05% slippage on fills
    initial_cash=100_000,
)

result = runner.run(
    DualMAMomentum,
    df,
    params={"fast_period": 20, "slow_period": 50},
)

print(result.total_return_pct)   # e.g. 34.2
print(result.num_trades)         # e.g. 12
```

### Transaction costs

**Commission** is charged as a percentage of trade value on both the entry and exit:

```
cost = trade_value × commission_rate
```

At 0.1% commission and $100,000 position size, each round-trip costs $200.

**Slippage** models the difference between the signal price and the actual fill price. Backtrader applies it as a percentage of the price on the fill bar:

```
fill_price = signal_price × (1 + slippage)   # for buys
fill_price = signal_price × (1 - slippage)   # for sells
```

These two costs together can significantly impact strategy profitability — particularly for high-frequency strategies with many trades. Always backtest with realistic costs.

### Analyzers

The runner attaches two Backtrader analyzers automatically:

| Analyzer | Used for |
|----------|---------|
| `TradeAnalyzer` | Counting closed trades |
| `TimeReturn` | Building the equity curve (portfolio value per bar) |

---

## BacktestResult

`quant_trading/backtest/results.py`

A dataclass that holds everything produced by one backtest run.

```python
@dataclass
class BacktestResult:
    strategy_name: str        # e.g. "DualMAMomentum"
    params: dict              # e.g. {"fast_period": 20, "slow_period": 50}
    start: date               # first bar date
    end: date                 # last bar date
    initial_cash: float       # starting portfolio value
    final_value: float        # ending portfolio value
    num_trades: int           # number of completed round-trips
    total_return_pct: float   # computed automatically in __post_init__
    equity_curve: DataFrame   # columns: equity, returns (DatetimeIndex)
```

### `compute_metrics()`

Lazily computes analytics from the equity curve:

```python
metrics = result.compute_metrics()
# {
#     "annualised_return":  0.142,   # 14.2% per year
#     "annualised_vol":     0.187,   # 18.7% annualised volatility
#     "sharpe":             0.761,
#     "sortino":            1.023,
#     "max_drawdown":      -0.213,   # -21.3%
# }
```

---

## Walk-Forward Splitting

`quant_trading/backtest/splitter.py`

The biggest risk in strategy research is overfitting — finding parameters that work on historical data but fail on new data. Walk-forward splitting addresses this by evaluating parameters on data they've never seen.

### How it works

```
Full dataset  (e.g. 1000 bars)
│
├── Fold 0
│   ├── TRAIN  bars 0–299   (fit parameters here)
│   └── TEST   bars 300–399 (evaluate here — held out)
│
└── Fold 1
    ├── TRAIN  bars 400–699
    └── TEST   bars 700–799
```

The test window steps forward by one test window per fold. Train and test windows never overlap.

```python
from quant_trading.backtest import walk_forward_splits

splits = walk_forward_splits(df, train_bars=750, test_bars=250)

for split in splits:
    print(f"Fold {split.fold}")
    print(f"  Train: {len(split.train)} bars")
    print(f"  Test:  {len(split.test)} bars")
```

### Choosing window sizes

For daily data:

| Window | Bars | Suitable for |
|--------|------|-------------|
| 1 year train | ~252 | Short-term strategies, limited data |
| 3 year train | ~756 | Standard — captures at least one market cycle |
| 5 year train | ~1260 | Long-term strategies, more stable parameter estimates |
| 1 year test | ~252 | Standard evaluation period |
| 6 month test | ~126 | More folds, higher variance per fold |

---

## Grid Search

`quant_trading/backtest/optimizer.py`

Exhaustively evaluates every combination of parameters on a dataset and returns results sorted by a chosen metric.

```python
from quant_trading.backtest import grid_search, BacktestRunner
from quant_trading.strategies import DualMAMomentum

runner = BacktestRunner()

results = grid_search(
    DualMAMomentum,
    train_df,
    param_grid={
        "fast_period": [10, 20, 30],
        "slow_period": [40, 60, 80, 100],
    },
    runner=runner,
    sort_by="total_return_pct",   # or "sharpe", "num_trades", etc.
)

# results is a list of BacktestResult, best first
best = results[0]
print(f"Best params: {best.params}")
print(f"Train return: {best.total_return_pct:.2f}%")
```

With 3 × 4 = 12 combinations, 12 backtests are run. Each combination is independent, so this is straightforward to parallelise in a future version.

---

## Walk-Forward Optimisation

`walk_forward_optimize` combines splitting and grid search into one call:

```python
from quant_trading.backtest import walk_forward_optimize

folds = walk_forward_optimize(
    DualMAMomentum,
    df,
    param_grid={
        "fast_period": [10, 20, 30],
        "slow_period": [40, 60, 80],
    },
    train_bars=750,
    test_bars=250,
)

for fold in folds:
    print(f"Fold {fold['fold']}")
    print(f"  Best params:   {fold['best_params']}")
    print(f"  Train return:  {fold['train_result'].total_return_pct:.2f}%")
    print(f"  Test return:   {fold['test_result'].total_return_pct:.2f}%")
```

**Interpreting results:**

- A large gap between train and test return suggests overfitting — the chosen parameters don't generalise.
- Consistent test returns across folds, even if lower than train, suggest a robust strategy.
- Negative test returns on a strategy with positive train returns is a strong signal to abandon the approach or reduce parameter space.

---

## Common Pitfalls

**Look-ahead bias.** Backtrader's `next()` method only receives data up to the current bar. Indicators are computed incrementally. There is no look-ahead by default — but be careful if you precompute signals outside of Backtrader and inject them as data.

**Survivorship bias.** The data layer fetches current tickers. If you backtest on `AAPL` from 2000, you're testing on a company you already know survived and thrived. For rigorous research, test on a universe of tickers including those that were delisted.

**Overfitting through repeated evaluation.** Every time you evaluate parameters on the test set and make a decision based on that result, you are effectively training on the test set. The test window should be evaluated exactly once — after parameters are locked in on the train set.
