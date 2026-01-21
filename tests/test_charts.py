"""グラフ生成テスト"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import matplotlib
matplotlib.use('Agg')  # GUIバックエンドを使わない
import matplotlib.pyplot as plt
import pytest

from betting_simulation.charts import (
    ChartGenerator,
    ChartConfig,
    FundChartGenerator,
    ProfitChartGenerator,
    RiskChartGenerator,
    StrategyChartGenerator,
    MonteCarloChartGenerator,
)
from betting_simulation.models import (
    SimulationResult,
    BetRecord,
    Ticket,
    TicketType,
    SimulationMetrics,
    Race,
    Horse,
    Surface,
)


def _create_mock_race(idx: int = 0) -> Race:
    """テスト用Raceを作成"""
    horses = [
        Horse(
            number=i,
            name=f"horse{i}",
            odds=5.0,
            popularity=i,
            actual_rank=i,
            predicted_rank=i,
            predicted_score=1.0 / i if i > 0 else 0,
        )
        for i in range(1, 6)
    ]
    return Race(
        track="Tokyo",
        year=2025,
        kaisai_date=101 + idx,
        race_number=1,
        surface=Surface.TURF,
        distance=1600,
        horses=horses,
    )


@pytest.fixture
def mock_result():
    """テスト用のシミュレーション結果"""
    bet_history = []
    current_fund = 100000
    fund_history = [current_fund]
    
    for i in range(50):
        is_hit = i % 5 == 0  # 20%的中
        ticket = Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),
            amount=1000,
            odds=5.0,
        )
        payout = 5000 if is_hit else 0
        
        fund_before = current_fund
        current_fund = current_fund - ticket.amount + payout
        
        bet_history.append(BetRecord(
            race=_create_mock_race(i),
            ticket=ticket,
            is_hit=is_hit,
            payout=payout,
            fund_before=fund_before,
            fund_after=current_fund,
        ))
        fund_history.append(current_fund)
    
    # メトリクス
    total_bets = len(bet_history)
    total_hits = sum(1 for r in bet_history if r.is_hit)
    total_invested = sum(r.ticket.amount for r in bet_history)
    total_payout = sum(r.payout for r in bet_history)
    
    metrics = SimulationMetrics(
        total_races=total_bets,
        total_bets=total_bets,
        total_hits=total_hits,
        total_invested=total_invested,
        total_payout=total_payout,
        hit_rate=total_hits / total_bets * 100 if total_bets > 0 else 0,
        roi=total_payout / total_invested * 100 if total_invested > 0 else 0,
        profit=total_payout - total_invested,
        max_drawdown=10.0,
    )
    
    return SimulationResult(
        initial_fund=100000,
        final_fund=current_fund,
        fund_history=fund_history,
        bet_history=bet_history,
        metrics=metrics,
    )


@pytest.fixture
def mock_results(mock_result):
    """テスト用の複数シミュレーション結果"""
    results = []
    for i in range(10):
        # 少しランダムに変動させる
        metrics = SimulationMetrics(
            total_races=mock_result.metrics.total_races,
            total_bets=mock_result.metrics.total_bets,
            total_hits=mock_result.metrics.total_hits,
            total_invested=mock_result.metrics.total_invested,
            total_payout=mock_result.metrics.total_payout,
            roi=mock_result.metrics.roi + (i - 5) * 2,
            hit_rate=mock_result.metrics.hit_rate,
            max_drawdown=mock_result.metrics.max_drawdown + i,
            profit=mock_result.metrics.profit,
        )
        result = SimulationResult(
            initial_fund=mock_result.initial_fund,
            final_fund=mock_result.final_fund + (i - 5) * 1000,
            fund_history=mock_result.fund_history.copy(),
            bet_history=mock_result.bet_history.copy(),
            metrics=metrics,
        )
        results.append(result)
    return results


class TestChartConfig:
    """ChartConfigのテスト"""
    
    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = ChartConfig()
        assert config.figsize == (12, 8)
        assert len(config.color_palette) > 0
        assert config.dpi == 100
    
    def test_custom_config(self):
        """カスタム設定のテスト"""
        config = ChartConfig(
            figsize=(10, 6),
            dpi=150,
            grid_alpha=0.5,
        )
        assert config.figsize == (10, 6)
        assert config.dpi == 150
        assert config.grid_alpha == 0.5


class TestFundChartGenerator:
    """FundChartGeneratorのテスト"""
    
    def test_generate_basic(self, mock_result):
        """基本グラフ生成テスト"""
        generator = FundChartGenerator()
        fig = generator.generate(mock_result, "basic")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_with_ma(self, mock_result):
        """移動平均付きグラフ生成テスト"""
        generator = FundChartGenerator()
        fig = generator.generate(mock_result, "with_ma", window=5)
        assert fig is not None
        plt.close(fig)
    
    def test_generate_with_target(self, mock_result):
        """目標ライン付きグラフ生成テスト"""
        generator = FundChartGenerator()
        fig = generator.generate(mock_result, "with_target", target=120000)
        assert fig is not None
        plt.close(fig)
    
    def test_generate_invalid_type(self, mock_result):
        """無効なグラフタイプのテスト"""
        generator = FundChartGenerator()
        with pytest.raises(ValueError, match="Unknown chart type"):
            generator.generate(mock_result, "invalid_type")
    
    def test_save_chart(self, mock_result):
        """グラフ保存テスト"""
        generator = FundChartGenerator()
        fig = generator.generate(mock_result, "basic")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_chart.png"
            saved_path = generator.save(fig, output_path)
            assert saved_path.exists()
            assert saved_path.suffix == ".png"
        
        plt.close(fig)


class TestProfitChartGenerator:
    """ProfitChartGeneratorのテスト"""
    
    def test_generate_roi_trend(self, mock_result):
        """ROI推移グラフテスト"""
        generator = ProfitChartGenerator()
        fig = generator.generate(mock_result, "roi_trend")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_hit_rate_trend(self, mock_result):
        """的中率推移グラフテスト"""
        generator = ProfitChartGenerator()
        fig = generator.generate(mock_result, "hit_rate_trend")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_roi_histogram(self, mock_result):
        """ROIヒストグラムテスト"""
        generator = ProfitChartGenerator()
        fig = generator.generate(mock_result, "roi_histogram")
        assert fig is not None
        plt.close(fig)


class TestRiskChartGenerator:
    """RiskChartGeneratorのテスト"""
    
    def test_generate_drawdown(self, mock_result):
        """ドローダウングラフテスト"""
        generator = RiskChartGenerator()
        fig = generator.generate(mock_result, "drawdown")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_streak(self, mock_result):
        """連敗/連勝グラフテスト"""
        generator = RiskChartGenerator()
        fig = generator.generate(mock_result, "streak")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_volatility(self, mock_result):
        """ボラティリティグラフテスト"""
        generator = RiskChartGenerator()
        fig = generator.generate(mock_result, "volatility")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_var(self, mock_result):
        """VaRグラフテスト"""
        generator = RiskChartGenerator()
        fig = generator.generate(mock_result, "var")
        assert fig is not None
        plt.close(fig)


class TestStrategyChartGenerator:
    """StrategyChartGeneratorのテスト"""
    
    def test_generate_performance(self, mock_result, mock_results):
        """パフォーマンス比較グラフテスト"""
        generator = StrategyChartGenerator()
        fig = generator.generate(mock_result, "performance", results=mock_results[:3])
        assert fig is not None
        plt.close(fig)
    
    def test_generate_timeline(self, mock_result):
        """タイムライングラフテスト"""
        generator = StrategyChartGenerator()
        fig = generator.generate(mock_result, "timeline")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_correlation(self, mock_result, mock_results):
        """相関ヒートマップテスト"""
        generator = StrategyChartGenerator()
        fig = generator.generate(mock_result, "correlation", results=mock_results[:3])
        assert fig is not None
        plt.close(fig)


class TestMonteCarloChartGenerator:
    """MonteCarloChartGeneratorのテスト"""
    
    def test_generate_distribution(self, mock_results):
        """分布グラフテスト"""
        generator = MonteCarloChartGenerator()
        fig = generator.generate(mock_results, "distribution")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_confidence(self, mock_results):
        """信頼区間グラフテスト"""
        generator = MonteCarloChartGenerator()
        fig = generator.generate(mock_results, "confidence")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_extremes(self, mock_results):
        """最悪/最良ケースグラフテスト"""
        generator = MonteCarloChartGenerator()
        fig = generator.generate(mock_results, "extremes")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_percentile(self, mock_results):
        """パーセンタイルグラフテスト"""
        generator = MonteCarloChartGenerator()
        fig = generator.generate(mock_results, "percentile")
        assert fig is not None
        plt.close(fig)
    
    def test_generate_convergence(self, mock_results):
        """収束分析グラフテスト"""
        generator = MonteCarloChartGenerator()
        fig = generator.generate(mock_results, "convergence")
        assert fig is not None
        plt.close(fig)


class TestGenerateAll:
    """generate_allメソッドのテスト"""
    
    def test_fund_generate_all(self, mock_result):
        """FundChartGenerator.generate_allテスト"""
        generator = FundChartGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = generator.generate_all(mock_result, tmpdir)
            assert len(saved) == 6  # 6種類のグラフ
            for path in saved:
                assert Path(path).exists()
    
    def test_profit_generate_all(self, mock_result):
        """ProfitChartGenerator.generate_allテスト"""
        generator = ProfitChartGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = generator.generate_all(mock_result, tmpdir)
            assert len(saved) == 8  # 8種類のグラフ
            for path in saved:
                assert Path(path).exists()
    
    def test_risk_generate_all(self, mock_result):
        """RiskChartGenerator.generate_allテスト"""
        generator = RiskChartGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            saved = generator.generate_all(mock_result, tmpdir)
            assert len(saved) == 6  # 6種類のグラフ
            for path in saved:
                assert Path(path).exists()
