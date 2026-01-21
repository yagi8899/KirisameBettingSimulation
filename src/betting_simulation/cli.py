"""CLI（コマンドラインインターフェース）"""

import json
import logging
import sys
from pathlib import Path

import click

from betting_simulation import __version__
from betting_simulation.config import ConfigLoader, SimulationConfig
from betting_simulation.data_loader import DataLoader
from betting_simulation.evaluator import BetEvaluator
from betting_simulation.fund_manager import FundManagerFactory
from betting_simulation.race_filter import RaceFilter
from betting_simulation.simulation_engine import SimulationEngine, StrategyComparator
from betting_simulation.strategy import StrategyFactory

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """競馬賭けシミュレーションシステム"""
    pass


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--monte-carlo", "-m", is_flag=True, help="モンテカルロシミュレーションを実行")
@click.option("--output", "-o", type=click.Path(), help="出力ファイルパス")
@click.option("--quiet", "-q", is_flag=True, help="進捗表示を抑制")
def run(config_path: str, monte_carlo: bool, output: str | None, quiet: bool) -> None:
    """シミュレーションを実行
    
    CONFIG_PATH: 設定ファイル（YAML）のパス
    """
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        # 設定読み込み
        config = ConfigLoader.load(config_path)
        
        # バリデーション
        errors = ConfigLoader.validate(config)
        if errors:
            for error in errors:
                click.echo(f"Error: {error}", err=True)
            sys.exit(1)
        
        click.echo(f"Configuration loaded: {config_path}")
        
        # データ読み込み
        loader = DataLoader()
        races = loader.load(config.data_path)
        click.echo(f"Loaded {len(races)} races")
        
        # フィルタリング
        race_filter = RaceFilter(config.filter_condition)
        filtered_races = race_filter.filter(races)
        click.echo(f"Filtered to {len(filtered_races)} races")
        
        if not filtered_races:
            click.echo("No races to simulate after filtering", err=True)
            sys.exit(1)
        
        # シミュレーションエンジン構築
        strategy = StrategyFactory.create(config.strategy_name, config.strategy_params)
        fund_manager = FundManagerFactory.create(
            config.fund_manager_name,
            config.fund_manager_params,
            config.fund_constraints
        )
        evaluator = BetEvaluator()
        engine = SimulationEngine(strategy, fund_manager, evaluator)
        
        click.echo(f"Strategy: {config.strategy_name}")
        click.echo(f"Fund Manager: {config.fund_manager_name}")
        click.echo(f"Initial Fund: {config.initial_fund:,}円")
        
        if monte_carlo:
            # モンテカルロシミュレーション
            click.echo(f"\nRunning Monte Carlo simulation ({config.monte_carlo_trials} trials)...")
            result = engine.run_monte_carlo(
                filtered_races,
                config.initial_fund,
                config.monte_carlo_trials,
                config.random_seed
            )
            _print_monte_carlo_result(result, config.initial_fund)
            
            if output:
                _save_monte_carlo_result(result, output)
        else:
            # シンプルシミュレーション
            click.echo("\nRunning simulation...")
            result = engine.run_simple(filtered_races, config.initial_fund)
            _print_simple_result(result)
            
            if output:
                _save_simple_result(result, output)
        
        click.echo("\nSimulation completed!")
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Simulation failed")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
def validate(config_path: str) -> None:
    """設定ファイルを検証
    
    CONFIG_PATH: 設定ファイル（YAML）のパス
    """
    try:
        config = ConfigLoader.load(config_path)
        errors = ConfigLoader.validate(config)
        
        if errors:
            click.echo("Validation failed:")
            for error in errors:
                click.echo(f"  - {error}")
            sys.exit(1)
        else:
            click.echo("Configuration is valid!")
            click.echo(f"  Strategy: {config.strategy_name}")
            click.echo(f"  Fund Manager: {config.fund_manager_name}")
            click.echo(f"  Initial Fund: {config.initial_fund:,}円")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("list-strategies")
def list_strategies() -> None:
    """利用可能な戦略を一覧表示"""
    strategies = StrategyFactory.list_strategies()
    
    click.echo("Available strategies:")
    for s in strategies:
        click.echo(f"  {s['name']}: {s['description']}")


@main.command("list-fund-managers")
def list_fund_managers() -> None:
    """利用可能な資金管理方式を一覧表示"""
    managers = FundManagerFactory.list_managers()
    
    click.echo("Available fund managers:")
    for m in managers:
        click.echo(f"  {m['name']}: {m['description']}")


@main.command("init-config")
@click.argument("output_path", type=click.Path())
def init_config(output_path: str) -> None:
    """サンプル設定ファイルを生成
    
    OUTPUT_PATH: 出力ファイルパス
    """
    config = SimulationConfig()
    config.data_path = "tsv/predicted_results_all.tsv"
    config.strategy_params = {"top_n": 1}
    config.fund_manager_params = {"bet_amount": 1000}
    
    ConfigLoader.save(config, output_path)
    click.echo(f"Sample configuration saved to: {output_path}")


@main.command("compare")
@click.argument("config_paths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="結果を保存するJSONファイルパス"
)
@click.option(
    "--csv", "-c",
    type=click.Path(),
    help="結果を保存するCSVファイルパス"
)
@click.option(
    "--sort-by", "-s",
    type=click.Choice(["roi", "hit_rate", "profit", "drawdown"]),
    default="roi",
    help="ソート基準（デフォルト: roi）"
)
@click.option(
    "--walk-forward", "-w",
    is_flag=True,
    help="Walk-Forwardシミュレーションを使用"
)
@click.option(
    "--window-size", "-ws",
    type=int,
    default=100,
    help="Walk-Forwardのウィンドウサイズ（デフォルト: 100）"
)
@click.option(
    "--step-size", "-ss",
    type=int,
    default=50,
    help="Walk-Forwardのステップサイズ（デフォルト: 50）"
)
def compare(
    config_paths: tuple,
    output: str | None,
    csv: str | None,
    sort_by: str,
    walk_forward: bool,
    window_size: int,
    step_size: int
) -> None:
    """複数の戦略を比較
    
    CONFIG_PATHS: 比較する設定ファイル（YAML）のパス（複数指定可）
    
    例: betting-sim compare config1.yaml config2.yaml config3.yaml
    """
    try:
        if len(config_paths) < 2:
            click.echo("Error: At least 2 config files are required for comparison", err=True)
            sys.exit(1)
        
        # 設定ファイルを読み込み
        configs = []
        for path in config_paths:
            config = ConfigLoader.load(path)
            configs.append(config)
            click.echo(f"Loaded: {path} (strategy: {config.strategy_name})")
        
        # 共通のデータを読み込み（最初の設定のdata_pathを使用）
        base_config = configs[0]
        click.echo(f"\nLoading data from: {base_config.data_path}")
        loader = DataLoader()
        races = loader.load(base_config.data_path)
        click.echo(f"Loaded {len(races)} races")
        
        # レースフィルタリング
        filter_instance = RaceFilter(base_config.filter_condition)
        filtered_races = filter_instance.filter(races)
        click.echo(f"Filtered to {len(filtered_races)} races")
        
        if not filtered_races:
            click.echo("Error: No races match the filter criteria", err=True)
            sys.exit(1)
        
        # 戦略比較を実行
        click.echo("\nComparing strategies...")
        comparator = StrategyComparator()
        
        # 戦略リストを作成
        strategies = []
        for config in configs:
            strategy = StrategyFactory.create(config.strategy_name, config.strategy_params)
            fund_manager = FundManagerFactory.create(config.fund_manager_name, config.fund_manager_params)
            strategies.append((config.strategy_name, strategy, fund_manager))
        
        results = comparator.compare(
            filtered_races,
            strategies,
            base_config.initial_fund
        )
        
        # 結果をソート
        sort_key_map = {
            "roi": lambda x: x.metrics.roi,
            "hit_rate": lambda x: x.metrics.hit_rate,
            "profit": lambda x: x.profit,
            "drawdown": lambda x: -x.metrics.max_drawdown  # 低いほうが良い
        }
        sorted_results = sorted(
            results.items(),
            key=lambda x: sort_key_map[sort_by](x[1]),
            reverse=True
        )
        
        # 結果を表示
        _print_comparison_result(sorted_results, sort_by, walk_forward)
        
        # サマリー統計
        summary_list = comparator.compare_summary(results)
        _print_comparison_summary_list(summary_list)
        
        # 結果を保存
        if output:
            _save_comparison_result(sorted_results, output)
        
        if csv:
            _save_comparison_csv(sorted_results, csv)
        
        click.echo("\nComparison completed!")
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Comparison failed")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _print_comparison_result(sorted_results: list, sort_by: str, is_walk_forward: bool) -> None:
    """比較結果を表示"""
    mode = "Walk-Forward" if is_walk_forward else "Simple"
    click.echo(f"\n{'=' * 80}")
    click.echo(f"Strategy Comparison Results ({mode} Mode, sorted by {sort_by})")
    click.echo("=" * 80)
    
    # ヘッダー
    click.echo(f"{'Rank':<5} {'Strategy':<20} {'Hit%':<8} {'ROI%':<10} {'Profit':<12} {'DD%':<8} {'Go?':<6}")
    click.echo("-" * 80)
    
    for rank, (name, result) in enumerate(sorted_results, 1):
        m = result.metrics
        go_status = click.style("GO", fg="green") if m.is_go else click.style("NO", fg="red")
        
        click.echo(
            f"{rank:<5} {name:<20} {m.hit_rate:<8.2f} {m.roi:<10.2f} "
            f"{result.profit:<+12,} {m.max_drawdown:<8.2f} {go_status}"
        )
    
    click.echo("=" * 80)


def _print_comparison_summary_list(summary_list: list[dict]) -> None:
    """比較サマリーを表示（リスト形式）"""
    click.echo("\n" + "-" * 40)
    click.echo("Summary Statistics")
    click.echo("-" * 40)
    
    if not summary_list:
        click.echo("No results to summarize")
        return
    
    # 各指標のベストを計算
    best_roi = max(summary_list, key=lambda x: x["roi"])
    best_hit = max(summary_list, key=lambda x: x["hit_rate"])
    lowest_dd = min(summary_list, key=lambda x: x["max_drawdown"])
    go_count = sum(1 for s in summary_list if s["is_go"])
    
    click.echo(f"Best ROI:      {best_roi['name']} ({best_roi['roi']:.2f}%)")
    click.echo(f"Best Hit Rate: {best_hit['name']} ({best_hit['hit_rate']:.2f}%)")
    click.echo(f"Lowest DD:     {lowest_dd['name']} ({lowest_dd['max_drawdown']:.2f}%)")
    click.echo(f"GO strategies: {go_count} / {len(summary_list)}")
    click.echo("-" * 40)


def _save_comparison_result(sorted_results: list, output_path: str) -> None:
    """比較結果をJSONで保存"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = []
    for name, result in sorted_results:
        data.append({
            "strategy": name,
            "initial_fund": result.initial_fund,
            "final_fund": result.final_fund,
            "profit": result.profit,
            "metrics": {
                "total_races": result.metrics.total_races,
                "total_bets": result.metrics.total_bets,
                "total_hits": result.metrics.total_hits,
                "hit_rate": result.metrics.hit_rate,
                "roi": result.metrics.roi,
                "max_drawdown": result.metrics.max_drawdown,
                "max_consecutive_losses": result.metrics.max_consecutive_losses,
                "is_go": result.metrics.is_go,
            }
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    click.echo(f"Comparison result saved to: {output_path}")


def _save_comparison_csv(sorted_results: list, output_path: str) -> None:
    """比較結果をCSVで保存"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    import csv as csv_module
    
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv_module.writer(f)
        writer.writerow([
            "Rank", "Strategy", "Initial", "Final", "Profit",
            "Races", "Bets", "Hits", "HitRate%", "ROI%", "MaxDD%", "MaxLossStreak", "IsGo"
        ])
        
        for rank, (name, result) in enumerate(sorted_results, 1):
            m = result.metrics
            writer.writerow([
                rank, name, result.initial_fund, result.final_fund, result.profit,
                m.total_races, m.total_bets, m.total_hits,
                f"{m.hit_rate:.2f}", f"{m.roi:.2f}", f"{m.max_drawdown:.2f}",
                m.max_consecutive_losses, "GO" if m.is_go else "NO-GO"
            ])
    
    click.echo(f"Comparison result saved to: {output_path}")


def _print_simple_result(result) -> None:
    """シンプルシミュレーション結果を表示"""
    metrics = result.metrics
    
    click.echo("\n" + "=" * 50)
    click.echo("Simulation Result")
    click.echo("=" * 50)
    click.echo(f"Initial Fund:    {result.initial_fund:>12,}円")
    click.echo(f"Final Fund:      {result.final_fund:>12,}円")
    click.echo(f"Profit/Loss:     {result.profit:>+12,}円")
    click.echo("-" * 50)
    click.echo(f"Total Races:     {metrics.total_races:>12,}")
    click.echo(f"Total Bets:      {metrics.total_bets:>12,}")
    click.echo(f"Total Hits:      {metrics.total_hits:>12,}")
    click.echo(f"Hit Rate:        {metrics.hit_rate:>12.2f}%")
    click.echo(f"ROI:             {metrics.roi:>12.2f}%")
    click.echo(f"Max Drawdown:    {metrics.max_drawdown:>12.2f}%")
    click.echo(f"Max Loss Streak: {metrics.max_consecutive_losses:>12,}")
    click.echo("-" * 50)
    
    if metrics.is_go:
        click.echo("Go/No-Go:        " + click.style("GO ✓", fg="green", bold=True))
    else:
        click.echo("Go/No-Go:        " + click.style("NO-GO ✗", fg="red", bold=True))
    
    click.echo("=" * 50)


def _print_monte_carlo_result(result, initial_fund: int) -> None:
    """モンテカルロ結果を表示"""
    click.echo("\n" + "=" * 50)
    click.echo("Monte Carlo Result")
    click.echo("=" * 50)
    click.echo(f"Trials:          {result.num_trials:>12,}")
    click.echo(f"Initial Fund:    {initial_fund:>12,}円")
    click.echo("-" * 50)
    click.echo(f"Mean Final:      {result.mean_final_fund:>12,.0f}円")
    click.echo(f"Median Final:    {result.median_final_fund:>12,.0f}円")
    click.echo(f"Std Dev:         {result.std_final_fund:>12,.0f}円")
    click.echo(f"Min Final:       {result.min_final_fund:>12,}円")
    click.echo(f"Max Final:       {result.max_final_fund:>12,}円")
    click.echo("-" * 50)
    click.echo(f"5th Percentile:  {result.percentile_5:>12,.0f}円")
    click.echo(f"25th Percentile: {result.percentile_25:>12,.0f}円")
    click.echo(f"75th Percentile: {result.percentile_75:>12,.0f}円")
    click.echo(f"95th Percentile: {result.percentile_95:>12,.0f}円")
    click.echo("-" * 50)
    click.echo(f"Profit Rate:     {result.profit_rate:>12.2f}%")
    click.echo(f"Bankruptcy Rate: {result.bankruptcy_rate:>12.2f}%")
    click.echo("=" * 50)


def _save_simple_result(result, output_path: str) -> None:
    """シンプルシミュレーション結果を保存"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "initial_fund": result.initial_fund,
        "final_fund": result.final_fund,
        "profit": result.profit,
        "metrics": {
            "total_races": result.metrics.total_races,
            "total_bets": result.metrics.total_bets,
            "total_hits": result.metrics.total_hits,
            "hit_rate": result.metrics.hit_rate,
            "roi": result.metrics.roi,
            "max_drawdown": result.metrics.max_drawdown,
            "max_consecutive_losses": result.metrics.max_consecutive_losses,
            "is_go": result.metrics.is_go,
        },
        "fund_history": result.fund_history,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    click.echo(f"Result saved to: {output_path}")


def _save_monte_carlo_result(result, output_path: str) -> None:
    """モンテカルロ結果を保存"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "num_trials": result.num_trials,
        "mean_final_fund": result.mean_final_fund,
        "median_final_fund": result.median_final_fund,
        "std_final_fund": result.std_final_fund,
        "min_final_fund": result.min_final_fund,
        "max_final_fund": result.max_final_fund,
        "percentile_5": result.percentile_5,
        "percentile_25": result.percentile_25,
        "percentile_75": result.percentile_75,
        "percentile_95": result.percentile_95,
        "profit_rate": result.profit_rate,
        "bankruptcy_rate": result.bankruptcy_rate,
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    click.echo(f"Result saved to: {output_path}")


if __name__ == "__main__":
    main()
