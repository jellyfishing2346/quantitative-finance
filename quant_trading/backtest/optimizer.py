import itertools
import pandas as pd
from .runner import BacktestRunner
from .results import BacktestResult

def grid_search(
    strategy_cls,
    train_df: pd.DataFrame,
    param_grid: dict,          # e.g. {"fast_period": [10,20], "slow_period": [30,50]}
    runner: BacktestRunner,
    sort_by: str = "total_return_pct",
) -> list[BacktestResult]:

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    results = []

    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        result = runner.run(strategy_cls, train_df, params=params)
        results.append(result)

    results.sort(key=lambda r: getattr(r, sort_by), reverse=True)
    return results

def walk_forward_optimize(
    strategy_cls,
    df: pd.DataFrame,
    param_grid: dict,
    train_bars: int = 750,
    test_bars: int = 250,
    runner: BacktestRunner = None,
) -> list[dict]:          # list of {fold, best_params, train_result, test_result}

    if runner is None:
        runner = BacktestRunner()

    splits = walk_forward_splits(df, train_bars, test_bars)
    fold_results = []

    for split in splits:
        train_results = grid_search(strategy_cls, split.train, param_grid, runner)
        best_params = train_results[0].params          # best on train
        test_result = runner.run(strategy_cls, split.test, params=best_params)
        fold_results.append({
            "fold": split.fold,
            "best_params": best_params,
            "train_result": train_results[0],
            "test_result": test_result,
        })

    return fold_results

