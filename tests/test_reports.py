"""レポート出力テスト"""

import json
import tempfile
from pathlib import Path

import pytest

from betting_simulation.reports import (
    JSONExporter,
    CSVExporter,
    TextExporter,
    ReportGenerator,
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
            name=f"馬{i}",
            odds=4.0,
            popularity=i,
            actual_rank=i,
            predicted_rank=i,
            predicted_score=1.0 / i if i > 0 else 0,
        )
        for i in range(1, 6)
    ]
    return Race(
        track="東京",
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
    
    for i in range(20):
        is_hit = i % 4 == 0  # 25%的中
        ticket = Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),
            amount=1000,
            odds=4.0,
        )
        payout = 4000 if is_hit else 0
        
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
        max_drawdown=15.0,
    )
    
    return SimulationResult(
        initial_fund=100000,
        final_fund=current_fund,
        fund_history=fund_history,
        bet_history=bet_history,
        metrics=metrics,
    )


class TestJSONExporter:
    """JSONExporterのテスト"""
    
    def test_export_summary_only(self, mock_result):
        """サマリーのみエクスポートテスト"""
        exporter = JSONExporter(include_history=False)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            result_path = exporter.export(mock_result, output_path)
            
            assert result_path.exists()
            
            with open(result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert "export_info" in data
            assert "summary" in data
            assert "metrics" in data
            assert "fund_history" not in data
            assert "bet_history" not in data
    
    def test_export_with_history(self, mock_result):
        """履歴付きエクスポートテスト"""
        exporter = JSONExporter(include_history=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            result_path = exporter.export(mock_result, output_path)
            
            with open(result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert "fund_history" in data
            assert "bet_history" in data
            assert len(data["bet_history"]) == len(mock_result.bet_history)
    
    def test_export_metrics(self, mock_result):
        """メトリクス出力テスト"""
        exporter = JSONExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            exporter.export(mock_result, output_path)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metrics = data["metrics"]
            assert "roi" in metrics
            assert "hit_rate" in metrics
            assert "max_drawdown" in metrics
            assert "profit" in metrics
            assert "sharpe_ratio" in metrics


class TestCSVExporter:
    """CSVExporterのテスト"""
    
    def test_export_creates_files(self, mock_result):
        """ファイル生成テスト"""
        exporter = CSVExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.csv"
            exporter.export(mock_result, output_path)
            
            # 3種類のCSVファイルが生成される
            assert (Path(tmpdir) / "report_summary.csv").exists()
            assert (Path(tmpdir) / "report_bets.csv").exists()
            assert (Path(tmpdir) / "report_fund_history.csv").exists()
    
    def test_export_summary_content(self, mock_result):
        """サマリー内容テスト"""
        exporter = CSVExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.csv"
            exporter.export(mock_result, output_path)
            
            summary_path = Path(tmpdir) / "report_summary.csv"
            with open(summary_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            assert "初期資金" in content
            assert "最終資金" in content
            assert "ROI" in content
    
    def test_export_bets_content(self, mock_result):
        """賭け履歴内容テスト"""
        exporter = CSVExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.csv"
            exporter.export(mock_result, output_path)
            
            bets_path = Path(tmpdir) / "report_bets.csv"
            with open(bets_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
            
            # ヘッダー + データ行
            assert len(lines) == len(mock_result.bet_history) + 1


class TestTextExporter:
    """TextExporterのテスト"""
    
    def test_export_creates_file(self, mock_result):
        """ファイル生成テスト"""
        exporter = TextExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.txt"
            result_path = exporter.export(mock_result, output_path)
            
            assert result_path.exists()
    
    def test_export_content(self, mock_result):
        """内容テスト"""
        exporter = TextExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.txt"
            exporter.export(mock_result, output_path)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "シミュレーション結果レポート" in content
            assert "基本情報" in content
            assert "賭け統計" in content
            assert "パフォーマンス指標" in content
            assert "総合判定" in content
    
    def test_export_grade_evaluation(self, mock_result):
        """評価グレードテスト"""
        exporter = TextExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.txt"
            exporter.export(mock_result, output_path)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 評価グレードが含まれる
            assert "評価グレード" in content


class TestReportGenerator:
    """ReportGeneratorのテスト"""
    
    def test_generate_all_formats(self, mock_result):
        """全形式生成テスト"""
        generator = ReportGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            results = generator.generate(mock_result, tmpdir)
            
            assert "json" in results
            assert "csv" in results
            assert "txt" in results
            
            assert results["json"].exists()
            assert results["txt"].exists()
    
    def test_generate_specific_formats(self, mock_result):
        """特定形式生成テスト"""
        generator = ReportGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            results = generator.generate(mock_result, tmpdir, formats=["json", "txt"])
            
            assert "json" in results
            assert "txt" in results
            assert "csv" not in results
    
    def test_generate_comparison_report(self, mock_result):
        """比較レポート生成テスト"""
        generator = ReportGenerator()
        
        # 複数の結果を作成
        results = [mock_result, mock_result, mock_result]
        names = ["戦略A", "戦略B", "戦略C"]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output = generator.generate_comparison_report(results, names, tmpdir)
            
            assert "json" in output
            assert "csv" in output
            assert "txt" in output
            
            # JSON内容確認
            with open(output["json"], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert "strategies" in data
            assert len(data["strategies"]) == 3
            assert "ranking" in data
    
    def test_comparison_csv_content(self, mock_result):
        """比較CSV内容テスト"""
        generator = ReportGenerator()
        
        results = [mock_result, mock_result]
        names = ["戦略A", "戦略B"]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output = generator.generate_comparison_report(results, names, tmpdir)
            
            with open(output["csv"], 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
            
            # ヘッダー + 2データ行
            assert len(lines) == 3
            assert "戦略A" in lines[1]
            assert "戦略B" in lines[2]
    
    def test_comparison_txt_ranking(self, mock_result):
        """比較テキストランキングテスト"""
        generator = ReportGenerator()
        
        results = [mock_result, mock_result, mock_result]
        names = ["戦略A", "戦略B", "戦略C"]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output = generator.generate_comparison_report(results, names, tmpdir)
            
            with open(output["txt"], 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "戦略比較レポート" in content
            assert "ROIランキング" in content
            assert "🥇" in content  # 1位の絵文字
