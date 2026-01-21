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
from betting_simulation.simulation_engine import SimulationEngine
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
