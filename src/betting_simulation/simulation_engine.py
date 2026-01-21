"""シミュレーションエンジン

賭けシミュレーションの実行と結果の集計を行う。
"""

import logging
import random
from typing import Optional

import numpy as np

from betting_simulation.evaluator import BetEvaluator
from betting_simulation.fund_manager import FundManager
from betting_simulation.models import (
    BetRecord,
    MonteCarloResult,
    Race,
    SimulationMetrics,
    SimulationResult,
)
from betting_simulation.strategy import Strategy

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """評価指標計算"""
    
    @staticmethod
    def calculate(result: SimulationResult) -> SimulationMetrics:
        """シミュレーション結果から評価指標を計算"""
        metrics = SimulationMetrics()
        
        if not result.bet_history:
            return metrics
        
        # 基本統計
        metrics.total_bets = len(result.bet_history)
        metrics.total_hits = sum(1 for b in result.bet_history if b.is_hit)
        metrics.total_invested = sum(b.ticket.amount for b in result.bet_history)
        metrics.total_payout = sum(b.payout for b in result.bet_history)
        
        # レース数（重複除去）
        race_ids = set(b.race.race_id for b in result.bet_history)
        metrics.total_races = len(race_ids)
        
        # 的中率
        if metrics.total_bets > 0:
            metrics.hit_rate = (metrics.total_hits / metrics.total_bets) * 100
        
        # ROI
        if metrics.total_invested > 0:
            metrics.roi = (metrics.total_payout / metrics.total_invested) * 100
        
        # 純利益
        metrics.profit = metrics.total_payout - metrics.total_invested
        
        # 最大ドローダウン
        if result.fund_history:
            max_dd, dd_period = MetricsCalculator._calculate_max_drawdown(result.fund_history)
            metrics.max_drawdown = max_dd
            metrics.max_drawdown_period = dd_period
        
        # 連勝・連敗
        max_wins, max_losses = MetricsCalculator._calculate_streaks(result.bet_history)
        metrics.max_consecutive_wins = max_wins
        metrics.max_consecutive_losses = max_losses
        
        # シャープレシオ
        if len(result.bet_history) >= 2:
            returns = [
                (b.payout - b.ticket.amount) / b.ticket.amount 
                for b in result.bet_history if b.ticket.amount > 0
            ]
            if returns:
                metrics.sharpe_ratio = MetricsCalculator._calculate_sharpe_ratio(returns)
        
        # Go/No-Go判定
        metrics.is_go = MetricsCalculator._evaluate_go_nogo(metrics)
        
        return metrics
    
    @staticmethod
    def _calculate_max_drawdown(fund_history: list[int]) -> tuple[float, int]:
        """最大ドローダウンを計算"""
        if not fund_history:
            return 0.0, 0
        
        max_fund = fund_history[0]
        max_drawdown = 0.0
        max_drawdown_period = 0
        current_dd_period = 0
        
        for fund in fund_history:
            if fund > max_fund:
                max_fund = fund
                current_dd_period = 0
            else:
                current_dd_period += 1
                drawdown = (max_fund - fund) / max_fund * 100 if max_fund > 0 else 0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_period = current_dd_period
        
        return max_drawdown, max_drawdown_period
    
    @staticmethod
    def _calculate_streaks(bet_history: list[BetRecord]) -> tuple[int, int]:
        """連勝・連敗を計算"""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for record in bet_history:
            if record.is_hit:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    @staticmethod
    def _calculate_sharpe_ratio(returns: list[float], risk_free_rate: float = 0.0) -> float:
        """シャープレシオを計算"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        return (mean_return - risk_free_rate) / std_return
    
    @staticmethod
    def _evaluate_go_nogo(metrics: SimulationMetrics) -> bool:
        """Go/No-Go判定"""
        # 判定基準（要件定義書より）
        # ROI >= 100% AND 最大DD <= 30% AND 的中率 >= 10%
        return (
            metrics.roi >= 100 and 
            metrics.max_drawdown <= 30 and 
            metrics.hit_rate >= 10
        )


class SimulationEngine:
    """シミュレーションエンジン"""
    
    def __init__(
        self,
        strategy: Strategy,
        fund_manager: FundManager,
        evaluator: BetEvaluator | None = None
    ) -> None:
        """初期化
        
        Args:
            strategy: 賭け戦略
            fund_manager: 資金管理
            evaluator: 的中判定（省略時はデフォルト）
        """
        self.strategy = strategy
        self.fund_manager = fund_manager
        self.evaluator = evaluator or BetEvaluator()
    
    def run_simple(
        self, 
        races: list[Race], 
        initial_fund: int
    ) -> SimulationResult:
        """シンプルシミュレーションを実行
        
        全レースを順番に処理する。
        
        Args:
            races: レースリスト
            initial_fund: 初期資金
            
        Returns:
            シミュレーション結果
        """
        current_fund = initial_fund
        bet_history: list[BetRecord] = []
        fund_history: list[int] = [initial_fund]
        
        self.fund_manager.set_fund(current_fund)
        
        for race in races:
            # 馬券生成
            tickets = self.strategy.generate_tickets(race)
            
            if not tickets:
                continue
            
            # 賭け金計算
            amounts = self.fund_manager.calculate_bet_amounts(tickets)
            
            for ticket, amount in zip(tickets, amounts):
                if amount <= 0:
                    continue
                
                ticket.amount = amount
                fund_before = current_fund
                
                # 賭け金を引く
                current_fund -= amount
                
                # 的中判定
                is_hit, payout = self.evaluator.evaluate(ticket, race)
                
                # 払戻を加算
                current_fund += payout
                
                # 記録
                record = BetRecord(
                    race=race,
                    ticket=ticket,
                    is_hit=is_hit,
                    payout=payout,
                    fund_before=fund_before,
                    fund_after=current_fund
                )
                bet_history.append(record)
                fund_history.append(current_fund)
                
                # 資金更新
                self.fund_manager.set_fund(current_fund)
                
                # 破産チェック
                if current_fund < self.fund_manager.constraints.min_bet:
                    logger.warning("Bankruptcy! Stopping simulation.")
                    break
            
            if current_fund < self.fund_manager.constraints.min_bet:
                break
        
        # 結果作成
        result = SimulationResult(
            initial_fund=initial_fund,
            final_fund=current_fund,
            bet_history=bet_history,
            fund_history=fund_history
        )
        
        # 評価指標計算
        result.metrics = MetricsCalculator.calculate(result)
        
        return result
    
    def run_monte_carlo(
        self,
        races: list[Race],
        initial_fund: int,
        num_trials: int = 10000,
        random_seed: Optional[int] = None
    ) -> MonteCarloResult:
        """モンテカルロシミュレーションを実行
        
        レース順序をシャッフルして複数回シミュレーション。
        
        Args:
            races: レースリスト
            initial_fund: 初期資金
            num_trials: 試行回数
            random_seed: 乱数シード（再現性用）
            
        Returns:
            モンテカルロ結果
        """
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)
        
        final_funds: list[int] = []
        
        for trial in range(num_trials):
            # レースをシャッフル
            shuffled_races = races.copy()
            random.shuffle(shuffled_races)
            
            # シミュレーション実行
            result = self.run_simple(shuffled_races, initial_fund)
            final_funds.append(result.final_fund)
            
            if (trial + 1) % 1000 == 0:
                logger.info(f"Monte Carlo progress: {trial + 1}/{num_trials}")
        
        # 統計計算
        mc_result = MonteCarloResult(
            num_trials=num_trials,
            final_funds=final_funds
        )
        
        funds_array = np.array(final_funds)
        mc_result.mean_final_fund = float(np.mean(funds_array))
        mc_result.median_final_fund = float(np.median(funds_array))
        mc_result.std_final_fund = float(np.std(funds_array))
        mc_result.min_final_fund = int(np.min(funds_array))
        mc_result.max_final_fund = int(np.max(funds_array))
        
        # パーセンタイル
        mc_result.percentile_5 = float(np.percentile(funds_array, 5))
        mc_result.percentile_25 = float(np.percentile(funds_array, 25))
        mc_result.percentile_75 = float(np.percentile(funds_array, 75))
        mc_result.percentile_95 = float(np.percentile(funds_array, 95))
        
        # 破産率・利益率
        bankruptcy_threshold = initial_fund * 0.1  # 10%以下を破産とみなす
        mc_result.bankruptcy_rate = float(np.sum(funds_array < bankruptcy_threshold) / num_trials * 100)
        mc_result.profit_rate = float(np.sum(funds_array > initial_fund) / num_trials * 100)
        
        return mc_result
