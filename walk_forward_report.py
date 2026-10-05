"""
Run a real walk-forward test and print the numbers for the portfolio page.

Put this file in the root of the quantitative-finance repo and run:
    python walk_forward_report.py
    python walk_forward_report.py --ticker SPY --start 2010-01-01 --end 2024-12-31

For each fold it picks the best parameters on the training window only,
then runs those exact parameters on the following test window it has never
seen. The out-of-sample Sharpe at the end is computed from all the test
windows stitched together, with the framework's default trading costs.
"""

import argparse

import pandas as pd

from quant_trading.analytics.metrics import sharpe_ratio
from quant_trading.backtest import BacktestRunner, walk_forward_optimize
from quant_trading.data.fetcher import DataFetcher
from quant_trading.strategies import BollingerMeanReversion, DualMAMomentum

STRATEGIES = {
    "ma": (
        DualMAMomentum,
        {"fast_period": [10, 20, 30, 50], "slow_period": [60, 100, 150, 200]},
    ),
    "bollinger": (
        BollingerMeanReversion,
        {"period": [10, 20, 30], "dev_factor": [1.5, 2.0, 2.5]},
    ),
}


def returns_of(result) -> pd.Series:
    if result.equity_curve is None:
        return pd.Series(dtype=float)
    return result.equity_curve["returns"].dropna()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="AAPL")
    ap.add_argument("--start", default="2014-01-01")
    ap.add_argument("--end", default="2023-12-31")
    ap.add_argument("--strategy", choices=STRATEGIES, default="ma")
    ap.add_argument("--train-bars", type=int, default=750)
    ap.add_argument("--test-bars", type=int, default=250)
    args = ap.parse_args()

    strategy_cls, grid = STRATEGIES[args.strategy]
    df = DataFetcher().fetch(args.ticker, args.start, args.end).to_dataframe()

    folds = walk_forward_optimize(
        strategy_cls,
        df,
        grid,
        train_bars=args.train_bars,
        test_bars=args.test_bars,
        runner=BacktestRunner(),
    )
    if not folds:
        print("Not enough data for even one fold. Use a longer date range or smaller windows.")
        return

    print(f"\n{args.ticker}  {args.start} to {args.end}  strategy={strategy_cls.__name__}")
    print(f"train={args.train_bars} bars, test={args.test_bars} bars, folds={len(folds)}\n")
    print(f"{'fold':>4}  {'best params':<40} {'train Sharpe':>12} {'test Sharpe':>12}")

    train_sharpes, test_returns = [], []
    for f in folds:
        tr = sharpe_ratio(returns_of(f["train_result"]))
        te = sharpe_ratio(returns_of(f["test_result"]))
        train_sharpes.append(tr)
        test_returns.append(returns_of(f["test_result"]))
        print(f"{f['fold']:>4}  {str(f['best_params']):<40} {tr:>12.2f} {te:>12.2f}")

    oos = sharpe_ratio(pd.concat(test_returns))
    print(f"\nAverage in-sample Sharpe:  {sum(train_sharpes) / len(train_sharpes):.2f}")
    print(f"Out-of-sample Sharpe:      {oos:.2f}   <- the number for the portfolio")
    print("\nCopy everything above into the chat.")


if __name__ == "__main__":
    main()
