"""収益分析グラフ（8種）

1. ROI推移グラフ
2. 的中率推移グラフ
3. 回収率ヒストグラム
4. 利益/損失分布
5. 馬券種別別収益
6. オッズ帯別収益
7. 期待値 vs 実績
8. 収益ヒートマップ
"""

from typing import Optional
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

from betting_simulation.charts.base import (
    ChartGenerator, ChartConfig, format_currency, format_percentage
)
from betting_simulation.models import SimulationResult, TicketType


class ProfitChartGenerator(ChartGenerator):
    """収益分析グラフジェネレーター"""
    
    def generate(self, result: SimulationResult, chart_type: str = "roi_trend", **kwargs) -> plt.Figure:
        """収益分析グラフを生成
        
        Args:
            result: シミュレーション結果
            chart_type: グラフ種別
                - "roi_trend": ROI推移
                - "hit_rate_trend": 的中率推移
                - "roi_histogram": 回収率ヒストグラム
                - "profit_distribution": 利益/損失分布
                - "by_ticket_type": 馬券種別別収益
                - "by_odds_range": オッズ帯別収益
                - "expected_vs_actual": 期待値 vs 実績
                - "heatmap": 収益ヒートマップ
            **kwargs: 追加オプション
            
        Returns:
            Figure
        """
        methods = {
            "roi_trend": self._generate_roi_trend,
            "hit_rate_trend": self._generate_hit_rate_trend,
            "roi_histogram": self._generate_roi_histogram,
            "profit_distribution": self._generate_profit_distribution,
            "by_ticket_type": self._generate_by_ticket_type,
            "by_odds_range": self._generate_by_odds_range,
            "expected_vs_actual": self._generate_expected_vs_actual,
            "heatmap": self._generate_heatmap,
        }
        
        method = methods.get(chart_type)
        if method is None:
            raise ValueError(f"Unknown chart type: {chart_type}")
        
        return method(result, **kwargs)
    
    def _generate_roi_trend(self, result: SimulationResult, window: int = 50, **kwargs) -> plt.Figure:
        """ROI推移グラフ"""
        fig, ax = self._create_figure()
        
        # 累積ROIを計算
        total_bet = 0
        total_return = 0
        rois = []
        
        for record in result.bet_history:
            total_bet += record.ticket.amount
            total_return += record.payout
            roi = (total_return / total_bet * 100) if total_bet > 0 else 0
            rois.append(roi)
        
        if not rois:
            ax.text(0.5, 0.5, "データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        x = range(len(rois))
        
        # ROI推移
        ax.plot(x, rois, color=self.main_color, linewidth=2, label="累積ROI")
        
        # 100%ライン（損益分岐点）
        ax.axhline(y=100, color=self._get_color(6), linestyle="--", alpha=0.7, label="損益分岐点")
        
        # 利益/損失ゾーンの塗りつぶし
        ax.fill_between(x, rois, 100,
                        where=[r >= 100 for r in rois],
                        color=self.profit_color, alpha=0.3)
        ax.fill_between(x, rois, 100,
                        where=[r < 100 for r in rois],
                        color=self.loss_color, alpha=0.3)
        
        # 最終ROI表示
        final_roi = rois[-1]
        color = self.profit_color if final_roi >= 100 else self.loss_color
        ax.annotate(f"最終ROI: {final_roi:.2f}%", 
                    xy=(len(rois) - 1, final_roi),
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=11, color=color, fontweight="bold")
        
        self._apply_common_style(ax,
                                  title="ROI推移",
                                  xlabel="賭け回数",
                                  ylabel="ROI (%)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_hit_rate_trend(self, result: SimulationResult, window: int = 50, **kwargs) -> plt.Figure:
        """的中率推移グラフ"""
        fig, ax = self._create_figure()
        
        # 累積的中率を計算
        total_bets = 0
        total_hits = 0
        hit_rates = []
        
        for record in result.bet_history:
            total_bets += 1
            if record.is_hit:
                total_hits += 1
            hit_rate = (total_hits / total_bets * 100) if total_bets > 0 else 0
            hit_rates.append(hit_rate)
        
        if not hit_rates:
            ax.text(0.5, 0.5, "データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        x = range(len(hit_rates))
        
        # 的中率推移
        ax.plot(x, hit_rates, color=self.main_color, linewidth=2, label="累積的中率")
        
        # 最終的中率表示
        final_rate = hit_rates[-1]
        ax.annotate(f"最終: {final_rate:.2f}%", 
                    xy=(len(hit_rates) - 1, final_rate),
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=11, fontweight="bold")
        
        self._apply_common_style(ax,
                                  title="的中率推移",
                                  xlabel="賭け回数",
                                  ylabel="的中率 (%)")
        ax.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_roi_histogram(self, result: SimulationResult, bins: int = 30, **kwargs) -> plt.Figure:
        """回収率ヒストグラム"""
        fig, ax = self._create_figure()
        
        # 個別賭けのROIを計算
        individual_rois = []
        for record in result.bet_history:
            if record.ticket.amount > 0:
                roi = (record.payout / record.ticket.amount) * 100
                individual_rois.append(roi)
        
        if not individual_rois:
            ax.text(0.5, 0.5, "データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        # ヒストグラム
        n, bins_edges, patches = ax.hist(individual_rois, bins=bins, 
                                          color=self.main_color, alpha=0.7, edgecolor="white")
        
        # 色分け（100%以上は緑、未満は赤）
        for patch, left_edge in zip(patches, bins_edges[:-1]):
            if left_edge >= 100:
                patch.set_facecolor(self.profit_color)
            else:
                patch.set_facecolor(self.loss_color)
        
        # 100%ライン
        ax.axvline(x=100, color=self._get_color(6), linestyle="--", linewidth=2, label="損益分岐点")
        
        # 統計情報
        mean_roi = np.mean(individual_rois)
        median_roi = np.median(individual_rois)
        ax.axvline(x=mean_roi, color=self._get_color(3), linestyle="-.", 
                   linewidth=1.5, label=f"平均: {mean_roi:.1f}%")
        
        self._apply_common_style(ax,
                                  title="回収率分布",
                                  xlabel="ROI (%)",
                                  ylabel="頻度")
        ax.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_profit_distribution(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """利益/損失分布グラフ"""
        fig, ax = self._create_figure()
        
        profits = [record.profit for record in result.bet_history]
        
        if not profits:
            ax.text(0.5, 0.5, "データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]
        zeros = [p for p in profits if p == 0]
        
        # 箱ひげ図
        data = []
        labels = []
        colors = []
        
        if wins:
            data.append(wins)
            labels.append(f"勝ち (n={len(wins)})")
            colors.append(self.profit_color)
        if losses:
            data.append(losses)
            labels.append(f"負け (n={len(losses)})")
            colors.append(self.loss_color)
        
        if data:
            bp = ax.boxplot(data, tick_labels=labels, patch_artist=True)
            for patch, color in zip(bp["boxes"], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        
        self._apply_common_style(ax,
                                  title="利益/損失分布",
                                  xlabel="",
                                  ylabel="金額 (円)")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_by_ticket_type(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """馬券種別別収益グラフ"""
        fig, ax = self._create_figure()
        
        # 馬券種別ごとに集計
        stats = defaultdict(lambda: {"bet": 0, "return": 0, "count": 0, "hits": 0})
        
        for record in result.bet_history:
            ticket_type = record.ticket.ticket_type.value
            stats[ticket_type]["bet"] += record.ticket.amount
            stats[ticket_type]["return"] += record.payout
            stats[ticket_type]["count"] += 1
            if record.is_hit:
                stats[ticket_type]["hits"] += 1
        
        if not stats:
            ax.text(0.5, 0.5, "データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        types = list(stats.keys())
        profits = [stats[t]["return"] - stats[t]["bet"] for t in types]
        rois = [(stats[t]["return"] / stats[t]["bet"] * 100) if stats[t]["bet"] > 0 else 0 for t in types]
        
        x = range(len(types))
        colors = [self.profit_color if p >= 0 else self.loss_color for p in profits]
        
        bars = ax.bar(x, profits, color=colors, alpha=0.8)
        
        # ROIをバーの上に表示
        for bar, roi in zip(bars, rois):
            height = bar.get_height()
            ax.annotate(f'{roi:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=10)
        
        ax.set_xticks(x)
        ax.set_xticklabels(types)
        ax.axhline(y=0, color=self._get_color(6), linestyle="-", linewidth=1)
        
        self._apply_common_style(ax,
                                  title="馬券種別別収益",
                                  xlabel="馬券種別",
                                  ylabel="損益 (円)")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_by_odds_range(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """オッズ帯別収益グラフ"""
        fig, ax = self._create_figure()
        
        # オッズ帯を定義
        odds_ranges = [
            (0, 2, "1.0-2.0"),
            (2, 5, "2.0-5.0"),
            (5, 10, "5.0-10.0"),
            (10, 20, "10.0-20.0"),
            (20, 50, "20.0-50.0"),
            (50, float("inf"), "50.0+"),
        ]
        
        stats = {label: {"bet": 0, "return": 0, "count": 0} for _, _, label in odds_ranges}
        
        for record in result.bet_history:
            odds = record.ticket.odds
            for low, high, label in odds_ranges:
                if low <= odds < high:
                    stats[label]["bet"] += record.ticket.amount
                    stats[label]["return"] += record.payout
                    stats[label]["count"] += 1
                    break
        
        labels = [label for _, _, label in odds_ranges if stats[label]["count"] > 0]
        profits = [stats[label]["return"] - stats[label]["bet"] for label in labels]
        counts = [stats[label]["count"] for label in labels]
        
        if not labels:
            ax.text(0.5, 0.5, "データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        x = range(len(labels))
        colors = [self.profit_color if p >= 0 else self.loss_color for p in profits]
        
        bars = ax.bar(x, profits, color=colors, alpha=0.8)
        
        # 件数をバーの上に表示
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            y_pos = height if height >= 0 else height - 500
            ax.annotate(f'n={count}',
                        xy=(bar.get_x() + bar.get_width() / 2, y_pos),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)
        
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45)
        ax.axhline(y=0, color=self._get_color(6), linestyle="-", linewidth=1)
        
        self._apply_common_style(ax,
                                  title="オッズ帯別収益",
                                  xlabel="オッズ帯",
                                  ylabel="損益 (円)")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_expected_vs_actual(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """期待値 vs 実績グラフ"""
        fig, ax = self._create_figure()
        
        expected = []
        actual = []
        
        for record in result.bet_history:
            if record.ticket.expected_value > 0:
                expected.append(record.ticket.expected_value)
                actual_roi = record.payout / record.ticket.amount if record.ticket.amount > 0 else 0
                actual.append(actual_roi)
        
        if not expected:
            ax.text(0.5, 0.5, "期待値データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        # 散布図
        ax.scatter(expected, actual, color=self.main_color, alpha=0.5, s=30)
        
        # 対角線（期待値=実績）
        max_val = max(max(expected), max(actual))
        ax.plot([0, max_val], [0, max_val], color=self._get_color(6), 
                linestyle="--", alpha=0.7, label="期待値=実績")
        
        # 相関係数
        if len(expected) > 2:
            corr = np.corrcoef(expected, actual)[0, 1]
            ax.annotate(f"相関: {corr:.3f}", xy=(0.05, 0.95), xycoords="axes fraction",
                        fontsize=11, fontweight="bold")
        
        self._apply_common_style(ax,
                                  title="期待値 vs 実績",
                                  xlabel="期待値",
                                  ylabel="実績 (ROI)")
        ax.legend(loc="lower right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_heatmap(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """収益ヒートマップ"""
        fig, ax = self._create_figure()
        
        # 月 x 曜日のヒートマップ（データがあれば）
        # ここでは簡易的に、レース番号 x トラックでヒートマップを作成
        
        track_profits = defaultdict(lambda: defaultdict(int))
        
        for record in result.bet_history:
            track = record.race.track
            race_num = record.race.race_number
            track_profits[track][race_num] += record.profit
        
        if not track_profits:
            ax.text(0.5, 0.5, "データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        tracks = list(track_profits.keys())
        race_nums = list(range(1, 13))  # 1-12R
        
        data = np.zeros((len(tracks), len(race_nums)))
        for i, track in enumerate(tracks):
            for j, race_num in enumerate(race_nums):
                data[i, j] = track_profits[track].get(race_num, 0)
        
        im = ax.imshow(data, cmap="RdYlGn", aspect="auto")
        
        ax.set_xticks(range(len(race_nums)))
        ax.set_xticklabels([f"{r}R" for r in race_nums])
        ax.set_yticks(range(len(tracks)))
        ax.set_yticklabels(tracks)
        
        plt.colorbar(im, ax=ax, label="損益 (円)")
        
        self._apply_common_style(ax,
                                  title="収益ヒートマップ（競馬場×レース番号）",
                                  xlabel="レース番号",
                                  ylabel="競馬場")
        
        plt.tight_layout()
        return fig
    
    def generate_all(self, result: SimulationResult, output_dir: str = "charts") -> list[str]:
        """全ての収益分析グラフを生成して保存"""
        from pathlib import Path
        output_path = Path(output_dir)
        
        chart_types = [
            ("roi_trend", "profit_roi_trend.png"),
            ("hit_rate_trend", "profit_hit_rate_trend.png"),
            ("roi_histogram", "profit_roi_histogram.png"),
            ("profit_distribution", "profit_distribution.png"),
            ("by_ticket_type", "profit_by_ticket_type.png"),
            ("by_odds_range", "profit_by_odds_range.png"),
            ("expected_vs_actual", "profit_expected_vs_actual.png"),
            ("heatmap", "profit_heatmap.png"),
        ]
        
        saved_files = []
        for chart_type, filename in chart_types:
            try:
                fig = self.generate(result, chart_type)
                filepath = self.save(fig, output_path / filename)
                saved_files.append(str(filepath))
            except Exception as e:
                print(f"Warning: Failed to generate {chart_type}: {e}")
        
        return saved_files
