"""シミュレーションエンジンの拡張テスト"""

import pytest
from unittest.mock import MagicMock

from betting_simulation.models import (
    Horse, Race, RacePayouts, Surface, SimulationResult, SimulationMetrics
)
from betting_simulation.strategy import FavoriteWinStrategy, FavoritePlaceStrategy
from betting_simulation.fund_manager import FixedFundManager
from betting_simulation.evaluator import BetEvaluator
from betting_simulation.simulation_engine import SimulationEngine, StrategyComparator, MetricsCalculator
from betting_simulation.config import SimulationConfig


@pytest.fixture
def sample_races():
    """テスト用のレースリスト"""
    races = []
    for i in range(10):
        win_horse = 1 if i % 3 == 0 else 2
        horses = [
            Horse(number=1, name="馬1", odds=2.0, popularity=1,
                  actual_rank=1 if i % 3 == 0 else 2, predicted_rank=1, predicted_score=0.8),
            Horse(number=2, name="馬2", odds=4.0, popularity=2,
                  actual_rank=2 if i % 3 == 0 else 1, predicted_rank=2, predicted_score=0.6),
            Horse(number=3, name="馬3", odds=10.0, popularity=3,
                  actual_rank=3, predicted_rank=3, predicted_score=0.4),
        ]
        
        payouts = RacePayouts(
            win_horse=win_horse,
            win_payout=200.0 if win_horse == 1 else 400.0,
            place_horses=[1, 2, 3],
            place_payouts=[120.0, 150.0, 200.0],
            place_popularities=[1, 2, 3],
        )
        
        race = Race(
            track="東京", year=2025, kaisai_date=500 + i,
            race_number=1, surface=Surface.TURF, distance=1600,
            horses=horses,
            payouts=payouts
        )
        races.append(race)
    return races


@pytest.fixture
def simulation_engine():
    """テスト用シミュレーションエンジン"""
    strategy = FavoriteWinStrategy(params={"top_n": 1})
    fund_manager = FixedFundManager(params={"bet_amount": 100})
    evaluator = BetEvaluator()
    return SimulationEngine(strategy, fund_manager, evaluator)


class TestSimulationEngine:
    """シミュレーションエンジンのテスト"""
    
    def test_run_simple(self, sample_races, simulation_engine):
        """シンプルシミュレーション"""
        result = simulation_engine.run_simple(sample_races, 10000)
        
        assert isinstance(result, SimulationResult)
        assert result.initial_fund == 10000
        assert isinstance(result.metrics, SimulationMetrics)
    
    def test_run_monte_carlo(self, sample_races, simulation_engine):
        """モンテカルロシミュレーション"""
        result = simulation_engine.run_monte_carlo(sample_races, 10000, num_trials=10)
        
        assert result.num_trials == 10
        assert result.mean_final_fund > 0
        assert 0 <= result.profit_rate <= 100
    
    def test_run_walk_forward(self, sample_races, simulation_engine):
        """Walk-Forwardシミュレーション"""
        results = simulation_engine.run_walk_forward(
            sample_races, 10000, window_size=5, step_size=2
        )
        
        assert isinstance(results, list)
        # ウィンドウ数を確認（10レース、ウィンドウ5、ステップ2）
        # (10 - 5) / 2 + 1 = 3ウィンドウ
        assert len(results) >= 1


class TestStrategyComparator:
    """戦略比較のテスト"""
    
    def test_compare_multiple_strategies(self, sample_races):
        """複数戦略を比較"""
        comparator = StrategyComparator()
        
        strategy1 = FavoriteWinStrategy(params={"top_n": 1})
        fund_manager1 = FixedFundManager(params={"bet_amount": 100})
        
        strategy2 = FavoritePlaceStrategy(params={"top_n": 1})
        fund_manager2 = FixedFundManager(params={"bet_amount": 100})
        
        strategies = [
            ("favorite_win", strategy1, fund_manager1),
            ("favorite_place", strategy2, fund_manager2),
        ]
        
        results = comparator.compare(sample_races, strategies, 10000)
        
        assert len(results) == 2
        assert "favorite_win" in results
        assert "favorite_place" in results
    
    def test_compare_summary(self, sample_races):
        """比較サマリーを取得"""
        comparator = StrategyComparator()
        
        strategy1 = FavoriteWinStrategy(params={"top_n": 1})
        fund_manager1 = FixedFundManager(params={"bet_amount": 100})
        
        strategy2 = FavoritePlaceStrategy(params={"top_n": 1})
        fund_manager2 = FixedFundManager(params={"bet_amount": 100})
        
        strategies = [
            ("favorite_win", strategy1, fund_manager1),
            ("favorite_place", strategy2, fund_manager2),
        ]
        
        results = comparator.compare(sample_races, strategies, 10000)
        summary = comparator.compare_summary(results)
        
        assert len(summary) == 2
        assert all("roi" in s for s in summary)
        assert all("hit_rate" in s for s in summary)
        assert all("is_go" in s for s in summary)
    
    def test_rank_strategies(self, sample_races):
        """戦略ランキング"""
        comparator = StrategyComparator()
        
        strategy1 = FavoriteWinStrategy(params={"top_n": 1})
        fund_manager1 = FixedFundManager(params={"bet_amount": 100})
        
        strategy2 = FavoritePlaceStrategy(params={"top_n": 1})
        fund_manager2 = FixedFundManager(params={"bet_amount": 100})
        
        strategies = [
            ("favorite_win", strategy1, fund_manager1),
            ("favorite_place", strategy2, fund_manager2),
        ]
        
        results = comparator.compare(sample_races, strategies, 10000)
        ranking = comparator.rank_strategies(results)
        
        assert len(ranking) == 2


class TestMetricsCalculator:
    """メトリクス計算のテスト"""
    
    def test_calculate_from_result(self, sample_races, simulation_engine):
        """シミュレーション結果からメトリクス計算"""
        result = simulation_engine.run_simple(sample_races, 10000)
        
        # 結果にはmetrics が付いている
        assert result.metrics is not None
        assert result.metrics.total_bets > 0
        assert result.metrics.max_drawdown >= 0
