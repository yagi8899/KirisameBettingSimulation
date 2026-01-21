"""戦略分析グラフ（5種）

1. 戦略別パフォーマンス比較
2. 戦略別リスク比較
3. 戦略切り替えタイムライン
4. パラメータ感度分析
5. 戦略相関ヒートマップ
"""

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from betting_simulation.charts.base import (
    ChartGenerator, ChartConfig, format_currency, format_percentage
)
from betting_simulation.models import SimulationResult


class StrategyChartGenerator(ChartGenerator):
    """戦略分析グラフジェネレーター"""
    
    def generate(self, result: SimulationResult, chart_type: str = "performance", 
                 results: list | None = None, **kwargs) -> plt.Figure:
        """戦略分析グラフを生成
        
        Args:
            result: シミュレーション結果（単一結果用）
            chart_type: グラフ種別
                - "performance": 戦略別パフォーマンス比較
                - "risk": 戦略別リスク比較
                - "timeline": 戦略切り替えタイムライン
                - "sensitivity": パラメータ感度分析
                - "correlation": 戦略相関ヒートマップ
            results: 複数のシミュレーション結果（比較用）
            **kwargs: 追加オプション
            
        Returns:
            Figure
        """
        methods = {
            "performance": self._generate_performance,
            "risk": self._generate_risk_comparison,
            "timeline": self._generate_timeline,
            "sensitivity": self._generate_sensitivity,
            "correlation": self._generate_correlation,
        }
        
        method = methods.get(chart_type)
        if method is None:
            raise ValueError(f"Unknown chart type: {chart_type}")
        
        return method(result, results=results, **kwargs)
    
    def _generate_performance(self, result: SimulationResult, results: list | None = None, 
                              strategy_names: list | None = None, **kwargs) -> plt.Figure:
        """戦略別パフォーマンス比較グラフ"""
        fig, axes = self._create_figure(nrows=2, ncols=2, figsize=(14, 12))
        ax1, ax2 = axes[0]
        ax3, ax4 = axes[1]
        
        # 複数結果がない場合は単一結果を使用
        if not results:
            results = [result]
        
        if not strategy_names:
            strategy_names = [f"戦略{i+1}" for i in range(len(results))]
        
        n = len(results)
        x = range(n)
        colors = [self._get_color(i) for i in range(n)]
        
        # 1. 最終ROI比較
        rois = [r.metrics.roi if r.metrics else 0 for r in results]
        bars1 = ax1.bar(x, rois, color=colors, alpha=0.8, edgecolor="white")
        
        # 損益分岐点ライン
        ax1.axhline(y=100, color=self._get_color(6), linestyle="--", alpha=0.7)
        
        # バーにラベル
        for bar, roi in zip(bars1, rois):
            height = bar.get_height()
            ax1.annotate(f'{roi:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(strategy_names, rotation=45, ha="right")
        self._apply_common_style(ax1, title="最終ROI比較", xlabel="", ylabel="ROI (%)")
        
        # 2. 的中率比較
        hit_rates = [r.metrics.hit_rate if r.metrics else 0 for r in results]
        bars2 = ax2.bar(x, hit_rates, color=colors, alpha=0.8, edgecolor="white")
        
        for bar, hr in zip(bars2, hit_rates):
            height = bar.get_height()
            ax2.annotate(f'{hr:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)
        
        ax2.set_xticks(x)
        ax2.set_xticklabels(strategy_names, rotation=45, ha="right")
        self._apply_common_style(ax2, title="的中率比較", xlabel="", ylabel="的中率 (%)")
        
        # 3. 資金推移比較
        for i, res in enumerate(results):
            label = strategy_names[i] if i < len(strategy_names) else f"戦略{i+1}"
            ax3.plot(res.fund_history, color=colors[i], linewidth=1.5, label=label, alpha=0.8)
        
        ax3.axhline(y=results[0].initial_fund if results else 0, 
                    color=self._get_color(6), linestyle=":", alpha=0.7, label="初期資金")
        
        self._apply_common_style(ax3, title="資金推移比較", xlabel="レース数", ylabel="資金 (円)")
        ax3.legend(loc="upper left", fontsize=self.config.legend_fontsize - 1)
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        # 4. 総合スコア（レーダーチャートの代替: バブルチャート）
        max_dds = [r.metrics.max_drawdown if r.metrics else 0 for r in results]
        profits = [r.metrics.profit if r.metrics else 0 for r in results]
        
        # サイズは的中率に比例
        sizes = [(hr + 10) * 5 for hr in hit_rates]
        
        scatter = ax4.scatter(max_dds, rois, s=sizes, c=colors, alpha=0.7, edgecolors="white", linewidths=2)
        
        for i, name in enumerate(strategy_names):
            ax4.annotate(name, xy=(max_dds[i], rois[i]), xytext=(5, 5), 
                         textcoords="offset points", fontsize=9)
        
        ax4.axhline(y=100, color=self._get_color(6), linestyle="--", alpha=0.5)
        
        self._apply_common_style(ax4, title="リスク vs リターン（サイズ=的中率）", 
                                  xlabel="最大ドローダウン (%)", ylabel="ROI (%)")
        
        plt.tight_layout()
        return fig
    
    def _generate_risk_comparison(self, result: SimulationResult, results: list | None = None,
                                   strategy_names: list | None = None, **kwargs) -> plt.Figure:
        """戦略別リスク比較グラフ"""
        fig, axes = self._create_figure(nrows=1, ncols=2, figsize=(14, 6))
        ax1, ax2 = axes
        
        if not results:
            results = [result]
        
        if not strategy_names:
            strategy_names = [f"戦略{i+1}" for i in range(len(results))]
        
        n = len(results)
        x = range(n)
        colors = [self._get_color(i) for i in range(n)]
        
        # 1. 最大ドローダウン比較
        max_dds = [r.metrics.max_drawdown if r.metrics else 0 for r in results]
        bars1 = ax1.bar(x, max_dds, color=[self.loss_color] * n, alpha=0.8, edgecolor="white")
        
        # 警告ラインs
        ax1.axhline(y=20, color=self._get_color(3), linestyle="--", alpha=0.7, label="警告20%")
        ax1.axhline(y=30, color=self.loss_color, linestyle="-.", alpha=0.7, label="危険30%")
        
        for bar, dd in zip(bars1, max_dds):
            height = bar.get_height()
            ax1.annotate(f'{dd:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(strategy_names, rotation=45, ha="right")
        self._apply_common_style(ax1, title="最大ドローダウン比較", xlabel="", ylabel="最大DD (%)")
        ax1.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        # 2. リスク指標まとめ（ボラティリティ推定）
        volatilities = []
        sharpes = []
        
        for res in results:
            # ボラティリティ計算
            if len(res.fund_history) > 1:
                returns = []
                for i in range(1, len(res.fund_history)):
                    if res.fund_history[i - 1] > 0:
                        ret = (res.fund_history[i] - res.fund_history[i - 1]) / res.fund_history[i - 1]
                        returns.append(ret)
                vol = np.std(returns) * 100 if returns else 0
                mean_ret = np.mean(returns) if returns else 0
                sharpe = mean_ret / np.std(returns) if returns and np.std(returns) > 0 else 0
            else:
                vol = 0
                sharpe = 0
            volatilities.append(vol)
            sharpes.append(sharpe)
        
        # 双軸グラフ
        bar_width = 0.35
        x_arr = np.arange(n)
        
        bars2a = ax2.bar(x_arr - bar_width/2, volatilities, bar_width, 
                         color=self.main_color, alpha=0.8, label="ボラティリティ (%)")
        ax2b = ax2.twinx()
        bars2b = ax2b.bar(x_arr + bar_width/2, sharpes, bar_width, 
                          color=self.profit_color, alpha=0.8, label="シャープレシオ")
        
        ax2.set_xticks(x_arr)
        ax2.set_xticklabels(strategy_names, rotation=45, ha="right")
        ax2.set_ylabel("ボラティリティ (%)")
        ax2b.set_ylabel("シャープレシオ")
        
        # 凡例を統合
        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2b.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=self.config.legend_fontsize)
        
        self._apply_common_style(ax2, title="リスク指標比較", xlabel="", ylabel="")
        
        plt.tight_layout()
        return fig
    
    def _generate_timeline(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """戦略切り替えタイムライン（動的戦略用）"""
        fig, (ax1, ax2) = self._create_figure(nrows=2, figsize=(14, 10))
        
        fund_history = result.fund_history
        x = range(len(fund_history))
        
        # 上段: 資金推移
        ax1.plot(x, fund_history, color=self.main_color, linewidth=1.5)
        ax1.fill_between(x, fund_history, result.initial_fund, 
                         where=[f >= result.initial_fund for f in fund_history],
                         color=self.profit_color, alpha=0.3)
        ax1.fill_between(x, fund_history, result.initial_fund, 
                         where=[f < result.initial_fund for f in fund_history],
                         color=self.loss_color, alpha=0.3)
        ax1.axhline(y=result.initial_fund, color=self._get_color(6), linestyle="--", alpha=0.7)
        
        self._apply_common_style(ax1, title="資金推移と戦略パフォーマンス", 
                                  xlabel="", ylabel="資金 (円)")
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        # 下段: ローリングパフォーマンス
        window = 20
        rolling_roi = []
        for i in range(len(fund_history)):
            start = max(0, i - window + 1)
            if fund_history[start] > 0:
                roi = (fund_history[i] / fund_history[start] - 1) * 100
            else:
                roi = 0
            rolling_roi.append(roi)
        
        ax2.plot(x, rolling_roi, color=self.main_color, linewidth=1.5)
        ax2.fill_between(x, rolling_roi, 0, 
                         where=[r >= 0 for r in rolling_roi],
                         color=self.profit_color, alpha=0.3)
        ax2.fill_between(x, rolling_roi, 0, 
                         where=[r < 0 for r in rolling_roi],
                         color=self.loss_color, alpha=0.3)
        ax2.axhline(y=0, color=self._get_color(6), linestyle="-", alpha=0.5)
        
        self._apply_common_style(ax2, title=f"ローリングROI ({window}期間)", 
                                  xlabel="レース数", ylabel="ROI (%)")
        
        plt.tight_layout()
        return fig
    
    def _generate_sensitivity(self, result: SimulationResult, param_results: dict | None = None,
                              **kwargs) -> plt.Figure:
        """パラメータ感度分析グラフ"""
        fig, ax = self._create_figure(figsize=(12, 8))
        
        # param_results: {param_name: [(value, roi), ...]}
        if not param_results:
            # サンプルデータ
            param_results = {
                "initial_fund": [(50000, 95), (100000, 100), (200000, 105), (500000, 108)],
                "bet_amount": [(100, 110), (500, 105), (1000, 100), (2000, 90), (5000, 75)],
            }
        
        for i, (param_name, data) in enumerate(param_results.items()):
            values = [d[0] for d in data]
            rois = [d[1] for d in data]
            
            # 正規化
            norm_values = np.array(values) / max(values) * 100
            
            ax.plot(norm_values, rois, color=self._get_color(i), linewidth=2, 
                    marker="o", markersize=8, label=param_name)
        
        ax.axhline(y=100, color=self._get_color(6), linestyle="--", alpha=0.7, label="損益分岐点")
        
        self._apply_common_style(ax, title="パラメータ感度分析", 
                                  xlabel="パラメータ値（正規化 %）", ylabel="ROI (%)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_correlation(self, result: SimulationResult, results: list | None = None,
                              strategy_names: list | None = None, **kwargs) -> plt.Figure:
        """戦略相関ヒートマップ"""
        fig, ax = self._create_figure(figsize=(10, 8))
        
        if not results or len(results) < 2:
            ax.text(0.5, 0.5, "比較には2つ以上の戦略が必要", 
                    transform=ax.transAxes, ha="center", va="center", fontsize=14)
            return fig
        
        if not strategy_names:
            strategy_names = [f"戦略{i+1}" for i in range(len(results))]
        
        # 各戦略のリターン系列を取得
        return_series = []
        min_len = min(len(r.fund_history) for r in results)
        
        for res in results:
            returns = []
            for i in range(1, min_len):
                if res.fund_history[i - 1] > 0:
                    ret = (res.fund_history[i] - res.fund_history[i - 1]) / res.fund_history[i - 1]
                else:
                    ret = 0
                returns.append(ret)
            return_series.append(returns)
        
        # 相関行列を計算
        n = len(results)
        corr_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    corr_matrix[i][j] = 1.0
                else:
                    if len(return_series[i]) > 0 and len(return_series[j]) > 0:
                        corr = np.corrcoef(return_series[i], return_series[j])[0, 1]
                        corr_matrix[i][j] = corr if not np.isnan(corr) else 0
                    else:
                        corr_matrix[i][j] = 0
        
        # ヒートマップ
        im = ax.imshow(corr_matrix, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")
        
        # カラーバー
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("相関係数", fontsize=12)
        
        # ラベル
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(strategy_names, rotation=45, ha="right")
        ax.set_yticklabels(strategy_names)
        
        # 値をセルに表示
        for i in range(n):
            for j in range(n):
                value = corr_matrix[i][j]
                color = "white" if abs(value) > 0.5 else "black"
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", 
                        fontsize=10, color=color, fontweight="bold")
        
        self._apply_common_style(ax, title="戦略間相関ヒートマップ", xlabel="", ylabel="")
        
        plt.tight_layout()
        return fig
    
    def generate_all(self, result: SimulationResult, results: list | None = None, 
                     output_dir: str = "charts") -> list[str]:
        """全ての戦略分析グラフを生成して保存"""
        from pathlib import Path
        output_path = Path(output_dir)
        
        chart_types = [
            ("performance", "strategy_performance.png"),
            ("risk", "strategy_risk.png"),
            ("timeline", "strategy_timeline.png"),
            ("sensitivity", "strategy_sensitivity.png"),
            ("correlation", "strategy_correlation.png"),
        ]
        
        saved_files = []
        for chart_type, filename in chart_types:
            try:
                fig = self.generate(result, chart_type, results=results)
                filepath = self.save(fig, output_path / filename)
                saved_files.append(str(filepath))
            except Exception as e:
                print(f"Warning: Failed to generate {chart_type}: {e}")
        
        return saved_files
