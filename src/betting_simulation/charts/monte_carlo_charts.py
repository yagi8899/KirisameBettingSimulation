"""モンテカルログラフ（8種）

1. シミュレーション結果分布
2. 信頼区間グラフ
3. 破産確率推移
4. 目標達成確率分析
5. 最悪/最良ケース分析
6. パーセンタイル推移
7. 収束分析グラフ
8. シナリオ比較グラフ
"""

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from betting_simulation.charts.base import (
    ChartGenerator, ChartConfig, format_currency, format_percentage
)
from betting_simulation.models import SimulationResult


class MonteCarloChartGenerator(ChartGenerator):
    """モンテカルログラフジェネレーター"""
    
    def generate(self, results: list[SimulationResult], chart_type: str = "distribution", 
                 **kwargs) -> plt.Figure:
        """モンテカルログラフを生成
        
        Args:
            results: 複数のシミュレーション結果（モンテカルロ試行）
            chart_type: グラフ種別
                - "distribution": シミュレーション結果分布
                - "confidence": 信頼区間グラフ
                - "bankruptcy": 破産確率推移
                - "target": 目標達成確率分析
                - "extremes": 最悪/最良ケース分析
                - "percentile": パーセンタイル推移
                - "convergence": 収束分析グラフ
                - "scenario": シナリオ比較グラフ
            **kwargs: 追加オプション
            
        Returns:
            Figure
        """
        methods = {
            "distribution": self._generate_distribution,
            "confidence": self._generate_confidence,
            "bankruptcy": self._generate_bankruptcy,
            "target": self._generate_target,
            "extremes": self._generate_extremes,
            "percentile": self._generate_percentile,
            "convergence": self._generate_convergence,
            "scenario": self._generate_scenario,
        }
        
        method = methods.get(chart_type)
        if method is None:
            raise ValueError(f"Unknown chart type: {chart_type}")
        
        return method(results, **kwargs)
    
    def _generate_distribution(self, results: list[SimulationResult], **kwargs) -> plt.Figure:
        """シミュレーション結果分布グラフ"""
        fig, (ax1, ax2) = self._create_figure(nrows=2, figsize=(12, 10))
        
        # 最終資金の分布
        final_funds = [r.final_fund for r in results]
        initial_fund = results[0].initial_fund if results else 0
        
        # 上段: ヒストグラム
        n, bins, patches = ax1.hist(final_funds, bins=50, color=self.main_color, 
                                     alpha=0.7, edgecolor="white")
        
        # 初期資金ライン
        ax1.axvline(x=initial_fund, color=self._get_color(3), linestyle="--", 
                    linewidth=2, label=f"初期資金: {format_currency(initial_fund)}")
        
        # 平均と中央値
        mean_fund = np.mean(final_funds)
        median_fund = np.median(final_funds)
        ax1.axvline(x=mean_fund, color=self.profit_color, linestyle="-", 
                    linewidth=2, label=f"平均: {format_currency(mean_fund)}")
        ax1.axvline(x=median_fund, color=self._get_color(5), linestyle="-.", 
                    linewidth=2, label=f"中央値: {format_currency(median_fund)}")
        
        # 損益分岐点以下を赤で塗りつぶし
        for patch, left_edge in zip(patches, bins[:-1]):
            if left_edge < initial_fund:
                patch.set_facecolor(self.loss_color)
        
        self._apply_common_style(ax1, title="最終資金分布", xlabel="最終資金 (円)", ylabel="頻度")
        ax1.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        # 下段: ROI分布
        rois = [r.metrics.roi if r.metrics else 0 for r in results]
        
        n2, bins2, patches2 = ax2.hist(rois, bins=50, color=self.main_color, 
                                        alpha=0.7, edgecolor="white")
        
        # 損益分岐点（100%）
        ax2.axvline(x=100, color=self._get_color(3), linestyle="--", 
                    linewidth=2, label="損益分岐点 (100%)")
        
        # 平均と中央値
        mean_roi = np.mean(rois)
        median_roi = np.median(rois)
        ax2.axvline(x=mean_roi, color=self.profit_color, linestyle="-", 
                    linewidth=2, label=f"平均: {mean_roi:.2f}%")
        ax2.axvline(x=median_roi, color=self._get_color(5), linestyle="-.", 
                    linewidth=2, label=f"中央値: {median_roi:.2f}%")
        
        # 100%以下を赤で塗りつぶし
        for patch, left_edge in zip(patches2, bins2[:-1]):
            if left_edge < 100:
                patch.set_facecolor(self.loss_color)
        
        self._apply_common_style(ax2, title="ROI分布", xlabel="ROI (%)", ylabel="頻度")
        ax2.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_confidence(self, results: list[SimulationResult], confidence: float = 0.95, 
                             **kwargs) -> plt.Figure:
        """信頼区間グラフ"""
        fig, ax = self._create_figure(figsize=(14, 8))
        
        # 各時点での資金分布を取得
        min_len = min(len(r.fund_history) for r in results)
        
        fund_matrix = np.array([r.fund_history[:min_len] for r in results])
        
        x = range(min_len)
        
        # 平均
        mean_funds = np.mean(fund_matrix, axis=0)
        ax.plot(x, mean_funds, color=self.main_color, linewidth=2, label="平均", zorder=5)
        
        # 信頼区間
        alpha = (1 - confidence) / 2
        lower_bound = np.percentile(fund_matrix, alpha * 100, axis=0)
        upper_bound = np.percentile(fund_matrix, (1 - alpha) * 100, axis=0)
        
        ax.fill_between(x, lower_bound, upper_bound, color=self.main_color, alpha=0.3,
                        label=f"{int(confidence*100)}%信頼区間")
        
        # 最大/最小
        min_funds = np.min(fund_matrix, axis=0)
        max_funds = np.max(fund_matrix, axis=0)
        ax.fill_between(x, min_funds, max_funds, color=self._get_color(4), alpha=0.1,
                        label="最大/最小範囲")
        
        # 初期資金ライン
        initial_fund = results[0].initial_fund
        ax.axhline(y=initial_fund, color=self._get_color(6), linestyle="--", 
                   alpha=0.7, label="初期資金")
        
        self._apply_common_style(ax, title=f"資金推移と{int(confidence*100)}%信頼区間", 
                                  xlabel="レース数", ylabel="資金 (円)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_bankruptcy(self, results: list[SimulationResult], threshold: float = 0.1, 
                             **kwargs) -> plt.Figure:
        """破産確率推移グラフ"""
        fig, (ax1, ax2) = self._create_figure(nrows=2, figsize=(12, 10))
        
        min_len = min(len(r.fund_history) for r in results)
        fund_matrix = np.array([r.fund_history[:min_len] for r in results])
        
        x = range(min_len)
        initial_fund = results[0].initial_fund
        bankruptcy_threshold = initial_fund * threshold
        
        # 上段: 破産確率推移
        bankruptcy_probs = []
        for i in range(min_len):
            bankrupt_count = np.sum(fund_matrix[:, i] < bankruptcy_threshold)
            prob = bankrupt_count / len(results) * 100
            bankruptcy_probs.append(prob)
        
        ax1.plot(x, bankruptcy_probs, color=self.loss_color, linewidth=2)
        ax1.fill_between(x, bankruptcy_probs, 0, color=self.loss_color, alpha=0.3)
        
        # 最終破産確率
        final_prob = bankruptcy_probs[-1]
        ax1.annotate(f"最終: {final_prob:.1f}%", xy=(min_len - 1, final_prob),
                     xytext=(-50, 10), textcoords="offset points",
                     fontsize=12, fontweight="bold", color=self.loss_color)
        
        self._apply_common_style(ax1, 
                                  title=f"破産確率推移（閾値: 初期資金の{int(threshold*100)}%以下）",
                                  xlabel="", ylabel="破産確率 (%)")
        
        # 下段: 資金が閾値を下回った回数のヒストグラム
        touch_counts = []
        for fund_history in fund_matrix:
            touches = np.sum(fund_history < bankruptcy_threshold)
            touch_counts.append(touches)
        
        ax2.hist(touch_counts, bins=20, color=self.loss_color, alpha=0.7, edgecolor="white")
        
        # ゼロ回の割合
        zero_touch = np.sum(np.array(touch_counts) == 0) / len(touch_counts) * 100
        ax2.annotate(f"一度も閾値を下回らなかった: {zero_touch:.1f}%", 
                     xy=(0.02, 0.95), xycoords="axes fraction",
                     fontsize=11, fontweight="bold")
        
        self._apply_common_style(ax2, title="閾値以下になった回数の分布",
                                  xlabel="閾値以下になった回数", ylabel="頻度")
        
        plt.tight_layout()
        return fig
    
    def _generate_target(self, results: list[SimulationResult], target_ratio: float = 1.5, 
                         **kwargs) -> plt.Figure:
        """目標達成確率分析グラフ"""
        fig, (ax1, ax2) = self._create_figure(nrows=2, figsize=(12, 10))
        
        min_len = min(len(r.fund_history) for r in results)
        fund_matrix = np.array([r.fund_history[:min_len] for r in results])
        
        x = range(min_len)
        initial_fund = results[0].initial_fund
        target_fund = initial_fund * target_ratio
        
        # 上段: 目標達成確率推移
        achievement_probs = []
        for i in range(min_len):
            achieved_count = np.sum(fund_matrix[:, i] >= target_fund)
            prob = achieved_count / len(results) * 100
            achievement_probs.append(prob)
        
        ax1.plot(x, achievement_probs, color=self.profit_color, linewidth=2)
        ax1.fill_between(x, achievement_probs, 0, color=self.profit_color, alpha=0.3)
        
        # 最終達成確率
        final_prob = achievement_probs[-1]
        ax1.annotate(f"最終: {final_prob:.1f}%", xy=(min_len - 1, final_prob),
                     xytext=(-50, 10), textcoords="offset points",
                     fontsize=12, fontweight="bold", color=self.profit_color)
        
        self._apply_common_style(ax1, 
                                  title=f"目標達成確率推移（目標: 初期資金の{int(target_ratio*100)}%）",
                                  xlabel="", ylabel="達成確率 (%)")
        
        # 下段: 目標達成までのレース数分布
        achievement_races = []
        for fund_history in fund_matrix:
            achieved = np.where(fund_history >= target_fund)[0]
            if len(achieved) > 0:
                achievement_races.append(achieved[0])
        
        if achievement_races:
            ax2.hist(achievement_races, bins=30, color=self.profit_color, alpha=0.7, edgecolor="white")
            
            mean_races = np.mean(achievement_races)
            ax2.axvline(x=mean_races, color=self.main_color, linestyle="--", linewidth=2,
                        label=f"平均: {mean_races:.0f}レース")
            ax2.legend(loc="upper right", fontsize=self.config.legend_fontsize)
            
            # 達成率
            achieved_rate = len(achievement_races) / len(results) * 100
            ax2.annotate(f"達成率: {achieved_rate:.1f}%", 
                         xy=(0.02, 0.95), xycoords="axes fraction",
                         fontsize=11, fontweight="bold")
        else:
            ax2.text(0.5, 0.5, "目標達成事例なし", transform=ax2.transAxes, 
                     ha="center", va="center", fontsize=14)
        
        self._apply_common_style(ax2, title="目標達成までのレース数分布",
                                  xlabel="レース数", ylabel="頻度")
        
        plt.tight_layout()
        return fig
    
    def _generate_extremes(self, results: list[SimulationResult], **kwargs) -> plt.Figure:
        """最悪/最良ケース分析グラフ"""
        fig, ax = self._create_figure(figsize=(14, 8))
        
        min_len = min(len(r.fund_history) for r in results)
        
        # 最終資金で最良/最悪を特定
        final_funds = [r.final_fund for r in results]
        best_idx = np.argmax(final_funds)
        worst_idx = np.argmin(final_funds)
        
        # 平均的なケース（中央値に最も近い）
        median_fund = np.median(final_funds)
        median_idx = np.argmin(np.abs(np.array(final_funds) - median_fund))
        
        x = range(min_len)
        
        # 全試行を薄くプロット
        for i, r in enumerate(results):
            ax.plot(r.fund_history[:min_len], color=self._get_color(4), 
                    alpha=0.05, linewidth=0.5)
        
        # 特定ケースを強調
        ax.plot(results[best_idx].fund_history[:min_len], color=self.profit_color, 
                linewidth=2.5, label=f"最良: {format_currency(final_funds[best_idx])}")
        ax.plot(results[worst_idx].fund_history[:min_len], color=self.loss_color, 
                linewidth=2.5, label=f"最悪: {format_currency(final_funds[worst_idx])}")
        ax.plot(results[median_idx].fund_history[:min_len], color=self.main_color, 
                linewidth=2, linestyle="--", label=f"中央値: {format_currency(final_funds[median_idx])}")
        
        # 初期資金ライン
        ax.axhline(y=results[0].initial_fund, color=self._get_color(6), linestyle=":", 
                   alpha=0.7, label="初期資金")
        
        self._apply_common_style(ax, title="最悪/最良ケース分析", 
                                  xlabel="レース数", ylabel="資金 (円)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_percentile(self, results: list[SimulationResult], **kwargs) -> plt.Figure:
        """パーセンタイル推移グラフ"""
        fig, ax = self._create_figure(figsize=(14, 8))
        
        min_len = min(len(r.fund_history) for r in results)
        fund_matrix = np.array([r.fund_history[:min_len] for r in results])
        
        x = range(min_len)
        
        # パーセンタイル計算
        percentiles = [10, 25, 50, 75, 90]
        colors = [self.loss_color, self._get_color(3), self.main_color, 
                  self._get_color(2), self.profit_color]
        
        for pct, color in zip(percentiles, colors):
            values = np.percentile(fund_matrix, pct, axis=0)
            ax.plot(x, values, color=color, linewidth=2, label=f"{pct}パーセンタイル")
        
        # 10-90パーセンタイル間を塗りつぶし
        p10 = np.percentile(fund_matrix, 10, axis=0)
        p90 = np.percentile(fund_matrix, 90, axis=0)
        ax.fill_between(x, p10, p90, color=self.main_color, alpha=0.2)
        
        # 25-75パーセンタイル間（IQR）
        p25 = np.percentile(fund_matrix, 25, axis=0)
        p75 = np.percentile(fund_matrix, 75, axis=0)
        ax.fill_between(x, p25, p75, color=self.main_color, alpha=0.3)
        
        # 初期資金ライン
        ax.axhline(y=results[0].initial_fund, color=self._get_color(6), linestyle="--", 
                   alpha=0.7, label="初期資金")
        
        self._apply_common_style(ax, title="パーセンタイル推移", 
                                  xlabel="レース数", ylabel="資金 (円)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_convergence(self, results: list[SimulationResult], **kwargs) -> plt.Figure:
        """収束分析グラフ"""
        fig, (ax1, ax2) = self._create_figure(nrows=2, figsize=(12, 10))
        
        # 試行回数ごとの平均ROIの収束
        rois = [r.metrics.roi if r.metrics else 0 for r in results]
        
        cumulative_means = []
        cumulative_stds = []
        for i in range(1, len(rois) + 1):
            cumulative_means.append(np.mean(rois[:i]))
            cumulative_stds.append(np.std(rois[:i], ddof=1) if i > 1 else 0)
        
        x = range(1, len(rois) + 1)
        
        # 上段: 累積平均ROI
        ax1.plot(x, cumulative_means, color=self.main_color, linewidth=2)
        ax1.axhline(y=cumulative_means[-1], color=self.profit_color, linestyle="--", 
                    alpha=0.7, label=f"最終平均: {cumulative_means[-1]:.2f}%")
        ax1.axhline(y=100, color=self._get_color(6), linestyle=":", alpha=0.7, label="損益分岐点")
        
        # 収束の目安（標準誤差のバンド）
        se = np.array(cumulative_stds) / np.sqrt(np.arange(1, len(rois) + 1))
        ax1.fill_between(x, np.array(cumulative_means) - 2*se, 
                         np.array(cumulative_means) + 2*se, 
                         color=self.main_color, alpha=0.2, label="±2標準誤差")
        
        self._apply_common_style(ax1, title="累積平均ROIの収束", 
                                  xlabel="試行回数", ylabel="平均ROI (%)")
        ax1.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        # 下段: 累積標準偏差の安定性
        ax2.plot(x, cumulative_stds, color=self.main_color, linewidth=2)
        ax2.axhline(y=cumulative_stds[-1], color=self._get_color(3), linestyle="--", 
                    alpha=0.7, label=f"最終標準偏差: {cumulative_stds[-1]:.2f}%")
        
        self._apply_common_style(ax2, title="累積標準偏差の安定性", 
                                  xlabel="試行回数", ylabel="標準偏差 (%)")
        ax2.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_scenario(self, results: list[SimulationResult], scenarios: dict | None = None,
                           scenario_names: list | None = None, **kwargs) -> plt.Figure:
        """シナリオ比較グラフ"""
        fig, (ax1, ax2) = self._create_figure(nrows=2, figsize=(14, 10))
        
        # scenarios: {scenario_name: [results]}
        if not scenarios:
            # 結果を3分割してシナリオとして扱う
            n = len(results)
            third = n // 3
            scenarios = {
                "シナリオA": results[:third],
                "シナリオB": results[third:2*third],
                "シナリオC": results[2*third:],
            }
        
        scenario_names = list(scenarios.keys()) if not scenario_names else scenario_names
        colors = [self._get_color(i) for i in range(len(scenarios))]
        
        # 上段: ROI分布の比較
        for i, (name, scenario_results) in enumerate(scenarios.items()):
            rois = [r.metrics.roi if r.metrics else 0 for r in scenario_results]
            ax1.hist(rois, bins=30, color=colors[i], alpha=0.5, label=name, edgecolor="white")
        
        ax1.axvline(x=100, color=self._get_color(6), linestyle="--", alpha=0.7)
        
        self._apply_common_style(ax1, title="シナリオ別ROI分布比較", 
                                  xlabel="ROI (%)", ylabel="頻度")
        ax1.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        # 下段: シナリオ別統計サマリー（箱ひげ図）
        all_rois = []
        for name, scenario_results in scenarios.items():
            rois = [r.metrics.roi if r.metrics else 0 for r in scenario_results]
            all_rois.append(rois)
        
        bp = ax2.boxplot(all_rois, labels=scenario_names, patch_artist=True)
        
        # 色付け
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax2.axhline(y=100, color=self._get_color(6), linestyle="--", alpha=0.7, label="損益分岐点")
        
        self._apply_common_style(ax2, title="シナリオ別ROI箱ひげ図", 
                                  xlabel="", ylabel="ROI (%)")
        ax2.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def generate_all(self, results: list[SimulationResult], output_dir: str = "charts") -> list[str]:
        """全てのモンテカルログラフを生成して保存"""
        from pathlib import Path
        output_path = Path(output_dir)
        
        chart_types = [
            ("distribution", "mc_distribution.png"),
            ("confidence", "mc_confidence.png"),
            ("bankruptcy", "mc_bankruptcy.png"),
            ("target", "mc_target.png"),
            ("extremes", "mc_extremes.png"),
            ("percentile", "mc_percentile.png"),
            ("convergence", "mc_convergence.png"),
            ("scenario", "mc_scenario.png"),
        ]
        
        saved_files = []
        for chart_type, filename in chart_types:
            try:
                fig = self.generate(results, chart_type)
                filepath = self.save(fig, output_path / filename)
                saved_files.append(str(filepath))
            except Exception as e:
                print(f"Warning: Failed to generate {chart_type}: {e}")
        
        return saved_files
