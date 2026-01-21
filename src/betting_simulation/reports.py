"""レポート出力モジュール

シミュレーション結果をJSON/CSV/TXT形式で出力
"""

import csv
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from betting_simulation.models import SimulationResult


class ReportExporter(ABC):
    """レポートエクスポーターの基底クラス"""
    
    @abstractmethod
    def export(self, result: SimulationResult, output_path: Path) -> Path:
        """結果をエクスポート"""
        pass


class JSONExporter(ReportExporter):
    """JSON形式でエクスポート"""
    
    def __init__(self, indent: int = 2, include_history: bool = False):
        """
        Args:
            indent: JSONインデント
            include_history: 履歴データを含めるか
        """
        self.indent = indent
        self.include_history = include_history
    
    def export(self, result: SimulationResult, output_path: Path) -> Path:
        """シミュレーション結果をJSONでエクスポート"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self._result_to_dict(result)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=self.indent, default=str)
        
        return output_path
    
    def _result_to_dict(self, result: SimulationResult) -> dict:
        """SimulationResultを辞書に変換"""
        m = result.metrics
        data = {
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "format": "json",
                "version": "1.0",
            },
            "summary": {
                "initial_fund": result.initial_fund,
                "final_fund": result.final_fund,
                "total_bets": m.total_bets if m else len(result.bet_history),
                "total_hits": m.total_hits if m else sum(1 for r in result.bet_history if r.is_hit),
                "total_invested": m.total_invested if m else sum(r.ticket.amount for r in result.bet_history),
                "total_payout": m.total_payout if m else sum(r.payout for r in result.bet_history),
            },
        }
        
        # メトリクス
        if result.metrics:
            data["metrics"] = {
                "roi": result.metrics.roi,
                "hit_rate": result.metrics.hit_rate,
                "max_drawdown": result.metrics.max_drawdown,
                "profit": result.metrics.profit,
                "sharpe_ratio": result.metrics.sharpe_ratio,
            }
        
        # 履歴データ（オプション）
        if self.include_history:
            data["fund_history"] = result.fund_history
            data["bet_history"] = [
                {
                    "race_id": record.race.race_id,
                    "ticket_type": str(record.ticket.ticket_type),
                    "amount": record.ticket.amount,
                    "odds": record.ticket.odds,
                    "is_hit": record.is_hit,
                    "payout": record.payout,
                }
                for record in result.bet_history
            ]
        
        return data


class CSVExporter(ReportExporter):
    """CSV形式でエクスポート"""
    
    def __init__(self, include_summary: bool = True, include_bets: bool = True):
        """
        Args:
            include_summary: サマリーファイルを生成するか
            include_bets: 個別賭けファイルを生成するか
        """
        self.include_summary = include_summary
        self.include_bets = include_bets
    
    def export(self, result: SimulationResult, output_path: Path) -> Path:
        """シミュレーション結果をCSVでエクスポート"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        base_name = output_path.stem
        output_dir = output_path.parent
        
        files_created = []
        
        # サマリーCSV
        if self.include_summary:
            summary_path = output_dir / f"{base_name}_summary.csv"
            self._export_summary(result, summary_path)
            files_created.append(summary_path)
        
        # 賭け履歴CSV
        if self.include_bets and result.bet_history:
            bets_path = output_dir / f"{base_name}_bets.csv"
            self._export_bets(result, bets_path)
            files_created.append(bets_path)
        
        # 資金推移CSV
        fund_path = output_dir / f"{base_name}_fund_history.csv"
        self._export_fund_history(result, fund_path)
        files_created.append(fund_path)
        
        return output_path if files_created else None
    
    def _export_summary(self, result: SimulationResult, path: Path):
        """サマリーをCSVでエクスポート"""
        m = result.metrics
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["項目", "値"])
            writer.writerow(["初期資金", result.initial_fund])
            writer.writerow(["最終資金", result.final_fund])
            writer.writerow(["総賭け回数", m.total_bets if m else len(result.bet_history)])
            writer.writerow(["的中回数", m.total_hits if m else sum(1 for r in result.bet_history if r.is_hit)])
            writer.writerow(["総賭け金額", m.total_invested if m else sum(r.ticket.amount for r in result.bet_history)])
            writer.writerow(["総払戻金", m.total_payout if m else sum(r.payout for r in result.bet_history)])
            
            if result.metrics:
                writer.writerow(["ROI (%)", f"{result.metrics.roi:.2f}"])
                writer.writerow(["的中率 (%)", f"{result.metrics.hit_rate:.2f}"])
                writer.writerow(["最大ドローダウン (%)", f"{result.metrics.max_drawdown:.2f}"])
                writer.writerow(["総利益", result.metrics.profit])

    def _export_bets(self, result: SimulationResult, path: Path):
        """賭け履歴をCSVでエクスポート"""
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["No", "レースID", "券種", "金額", "オッズ", "的中", "払戻金", "損益"])
            
            for i, record in enumerate(result.bet_history, 1):
                profit = record.payout - record.ticket.amount
                writer.writerow([
                    i,
                    record.race.race_id,
                    str(record.ticket.ticket_type),
                    record.ticket.amount,
                    record.ticket.odds,
                    "○" if record.is_hit else "×",
                    record.payout,
                    profit,
                ])
    
    def _export_fund_history(self, result: SimulationResult, path: Path):
        """資金推移をCSVでエクスポート"""
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["No", "資金", "前回比", "前回比(%)"])
            
            prev_fund = result.initial_fund
            for i, fund in enumerate(result.fund_history):
                diff = fund - prev_fund
                diff_pct = (diff / prev_fund * 100) if prev_fund > 0 else 0
                writer.writerow([i, fund, diff, f"{diff_pct:.2f}"])
                prev_fund = fund


class TextExporter(ReportExporter):
    """テキスト形式でエクスポート（人間可読）"""
    
    def __init__(self, width: int = 60):
        self.width = width
    
    def export(self, result: SimulationResult, output_path: Path) -> Path:
        """シミュレーション結果をテキストでエクスポート"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        lines = self._generate_report(result)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return output_path
    
    def _generate_report(self, result: SimulationResult) -> list[str]:
        """レポートテキストを生成"""
        lines = []
        sep = "=" * self.width
        subsep = "-" * self.width
        
        lines.append(sep)
        lines.append("シミュレーション結果レポート".center(self.width - 10))
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(sep)
        
        m = result.metrics
        
        # 基本情報
        lines.append("")
        lines.append("【基本情報】")
        lines.append(subsep)
        lines.append(f"初期資金: {result.initial_fund:>15,} 円")
        lines.append(f"最終資金: {result.final_fund:>15,} 円")
        lines.append(f"損益:     {result.final_fund - result.initial_fund:>+15,} 円")
        
        # 賭け統計
        total_bets = m.total_bets if m else len(result.bet_history)
        total_hits = m.total_hits if m else sum(1 for r in result.bet_history if r.is_hit)
        total_invested = m.total_invested if m else sum(r.ticket.amount for r in result.bet_history)
        total_payout = m.total_payout if m else sum(r.payout for r in result.bet_history)
        
        lines.append("")
        lines.append("【賭け統計】")
        lines.append(subsep)
        lines.append(f"総賭け回数: {total_bets:>12,} 回")
        lines.append(f"的中回数:   {total_hits:>12,} 回")
        lines.append(f"総賭け金額: {total_invested:>12,} 円")
        lines.append(f"総払戻金:   {total_payout:>12,} 円")
        
        # パフォーマンス指標
        if result.metrics:
            lines.append("")
            lines.append("【パフォーマンス指標】")
            lines.append(subsep)
            lines.append(f"ROI:               {result.metrics.roi:>10.2f} %")
            lines.append(f"的中率:            {result.metrics.hit_rate:>10.2f} %")
            lines.append(f"最大ドローダウン:  {result.metrics.max_drawdown:>10.2f} %")
            lines.append(f"シャープレシオ:    {result.metrics.sharpe_ratio:>10.2f}")
        
        # 判定
        lines.append("")
        lines.append("【総合判定】")
        lines.append(subsep)
        
        if result.metrics:
            roi = result.metrics.roi
            if roi >= 120:
                grade = "優秀 (A)"
            elif roi >= 110:
                grade = "良好 (B)"
            elif roi >= 100:
                grade = "プラス (C)"
            elif roi >= 90:
                grade = "軽微な損失 (D)"
            else:
                grade = "要改善 (E)"
            
            lines.append(f"評価グレード: {grade}")
            
            if result.metrics.max_drawdown > 30:
                lines.append("⚠️ 警告: 最大ドローダウンが30%を超えています")
            
            if result.metrics.hit_rate < 5:  # 5% (既にパーセント単位)
                lines.append("⚠️ 警告: 的中率が5%未満です")
        
        lines.append("")
        lines.append(sep)
        
        return lines


class ReportGenerator:
    """統合レポートジェネレーター"""
    
    def __init__(self):
        self.exporters = {
            "json": JSONExporter(include_history=True),
            "json_summary": JSONExporter(include_history=False),
            "csv": CSVExporter(),
            "txt": TextExporter(),
        }
    
    def generate(self, result: SimulationResult, output_dir: str | Path, 
                 formats: list[str] | None = None, base_name: str = "report") -> dict[str, Path]:
        """複数形式でレポートを生成
        
        Args:
            result: シミュレーション結果
            output_dir: 出力ディレクトリ
            formats: 出力形式リスト（None=全形式）
            base_name: ベースファイル名
            
        Returns:
            {format: output_path} の辞書
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if formats is None:
            formats = ["json", "csv", "txt"]
        
        results = {}
        for fmt in formats:
            exporter = self.exporters.get(fmt)
            if exporter is None:
                print(f"Warning: Unknown format '{fmt}'")
                continue
            
            ext = "json" if fmt.startswith("json") else fmt
            output_path = output_dir / f"{base_name}.{ext}"
            
            try:
                path = exporter.export(result, output_path)
                results[fmt] = path
            except Exception as e:
                print(f"Warning: Failed to export {fmt}: {e}")
        
        return results
    
    def generate_comparison_report(self, results: list[SimulationResult], 
                                   strategy_names: list[str],
                                   output_dir: str | Path,
                                   base_name: str = "comparison") -> dict[str, Path]:
        """戦略比較レポートを生成"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON比較レポート
        json_path = output_dir / f"{base_name}.json"
        comparison_data = {
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "format": "comparison_json",
                "version": "1.0",
                "strategy_count": len(results),
            },
            "strategies": [],
        }
        
        for name, result in zip(strategy_names, results):
            m = result.metrics
            strategy_data = {
                "name": name,
                "initial_fund": result.initial_fund,
                "final_fund": result.final_fund,
                "total_bets": m.total_bets if m else len(result.bet_history),
                "total_hits": m.total_hits if m else sum(1 for r in result.bet_history if r.is_hit),
            }
            if result.metrics:
                strategy_data["metrics"] = {
                    "roi": result.metrics.roi,
                    "hit_rate": result.metrics.hit_rate,
                    "max_drawdown": result.metrics.max_drawdown,
                }
            comparison_data["strategies"].append(strategy_data)
        
        # ランキング
        if results:
            sorted_strategies = sorted(
                zip(strategy_names, results),
                key=lambda x: x[1].metrics.roi if x[1].metrics else 0,
                reverse=True
            )
            comparison_data["ranking"] = [
                {"rank": i+1, "name": name, "roi": r.metrics.roi if r.metrics else 0}
                for i, (name, r) in enumerate(sorted_strategies)
            ]
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, ensure_ascii=False, indent=2, default=str)
        
        # CSV比較レポート
        csv_path = output_dir / f"{base_name}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                "戦略名", "初期資金", "最終資金", "総賭け回数", "的中回数",
                "ROI (%)", "的中率 (%)", "最大DD (%)"
            ])
            for name, result in zip(strategy_names, results):
                m = result.metrics
                total_bets = m.total_bets if m else len(result.bet_history)
                total_hits = m.total_hits if m else sum(1 for r in result.bet_history if r.is_hit)
                writer.writerow([
                    name,
                    result.initial_fund,
                    result.final_fund,
                    total_bets,
                    total_hits,
                    f"{m.roi:.2f}" if m else "N/A",
                    f"{m.hit_rate:.2f}" if m else "N/A",
                    f"{m.max_drawdown:.2f}" if m else "N/A",
                ])
        
        # テキスト比較レポート
        txt_path = output_dir / f"{base_name}.txt"
        lines = self._generate_comparison_text(results, strategy_names)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return {"json": json_path, "csv": csv_path, "txt": txt_path}
    
    def _generate_comparison_text(self, results: list[SimulationResult], 
                                   names: list[str]) -> list[str]:
        """比較レポートテキストを生成"""
        lines = []
        sep = "=" * 70
        subsep = "-" * 70
        
        lines.append(sep)
        lines.append("戦略比較レポート".center(60))
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"比較戦略数: {len(results)}")
        lines.append(sep)
        
        # サマリーテーブル
        lines.append("")
        lines.append("【サマリー】")
        lines.append(subsep)
        lines.append(f"{'戦略名':<15} {'ROI':>10} {'的中率':>10} {'最大DD':>10} {'最終資金':>15}")
        lines.append(subsep)
        
        for name, result in zip(names, results):
            m = result.metrics
            roi = f"{m.roi:.2f}%" if m else "N/A"
            hit = f"{m.hit_rate:.2f}%" if m else "N/A"
            dd = f"{m.max_drawdown:.2f}%" if m else "N/A"
            lines.append(f"{name:<15} {roi:>10} {hit:>10} {dd:>10} {result.final_fund:>15,}")
        
        # ランキング
        lines.append("")
        lines.append("【ROIランキング】")
        lines.append(subsep)
        
        sorted_data = sorted(
            zip(names, results),
            key=lambda x: x[1].metrics.roi if x[1].metrics else 0,
            reverse=True
        )
        
        for rank, (name, result) in enumerate(sorted_data, 1):
            roi = result.metrics.roi if result.metrics else 0
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
            lines.append(f"{emoji} {name}: ROI {roi:.2f}%")
        
        lines.append("")
        lines.append(sep)
        
        return lines
