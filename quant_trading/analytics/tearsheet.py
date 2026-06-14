import pandas as pd
import quantstats as qs

def generate_tearsheet(returns: pd.Series, output_path: str, title: str = "Strategy") -> None:
    qs.reports.html(returns, output=output_path, title=title)

def print_stats(returns: pd.Series) -> None:
    qs.reports.metrics(returns, mode="full")
