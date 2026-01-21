"""リスク分析グラフ（6種）

1. ドローダウングラフ
2. 連敗/連勝分析
3. 資金変動率グラフ
4. リスク・リターン散布図
5. バリュー・アット・リスク (VaR)
6. シャープレシオ推移
"""

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from betting_simulation.charts.base import (
    ChartGenerator, ChartConfig, format_currency, format_percentage
)
from betting_simulation.models import SimulationResult


class RiskChartGenerator(ChartGenerator):
    """リスク分析グラフジェネレーター"""
    
    def generate(self, result: SimulationResult, chart_type: str = "drawdown", **kwargs) -> plt.Figure:
        """リスク分析グラフを生成
        
        Args:
            result: シミュレーション結果
            chart_type: グラフ種別
                - "drawdown": ドローダウン
                - "streak": 連敗/連勝分析
                - "volatility": 資金変動率
                - "risk_return": リスク・リターン散布図
                - "var": バリュー・アット・リスク
                - "sharpe": シャープレシオ推移
            **kwargs: 追加オプション
            
        Returns:
            Figure
        """
        methods = {
            "drawdown": self._generate_drawdown,
            "streak": self._generate_streak,
            "volatility": self._generate_volatility,
            "risk_return": self._generate_risk_return,
            "var": self._generate_var,
            "sharpe": self._generate_sharpe,
        }
        
        method = methods.get(chart_type)
        if method is None:
            raise ValueError(f"Unknown chart type: {chart_type}")
        
        return method(result, **kwargs)
    
    def _generate_drawdown(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """ドローダウングラフ"""
        fig, (ax1, ax2) = self._create_figure(nrows=2, figsize=(12, 10))
        
        fund_history = result.fund_history
        x = range(len(fund_history))
        
        # 上段: 資金推移と最高値
        running_max = np.maximum.accumulate(fund_history)
        ax1.plot(x, fund_history, color=self.main_color, linewidth=1.5, label="資金")
        ax1.plot(x, running_max, color=self.profit_color, linestyle="--", linewidth=1, label="最高値")
        
        self._apply_common_style(ax1,
                                  title="資金推移と最高値",
                                  xlabel="",
                                  ylabel="資金 (円)")
        ax1.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        # 下段: ドローダウン率
        drawdowns = []
        for i, (fund, max_fund) in enumerate(zip(fund_history, running_max)):
            if max_fund > 0:
                dd = (max_fund - fund) / max_fund * 100
            else:
                dd = 0
            drawdowns.append(dd)
        
        ax2.fill_between(x, drawdowns, 0, color=self.loss_color, alpha=0.5)
        ax2.plot(x, drawdowns, color=self.loss_color, linewidth=1)
        
        # 最大ドローダウンをマーク
        max_dd = max(drawdowns)
        max_dd_idx = drawdowns.index(max_dd)
        ax2.scatter([max_dd_idx], [max_dd], color=self.loss_color, s=100, zorder=5)
        ax2.annotate(f"最大DD: {max_dd:.2f}%", 
                     xy=(max_dd_idx, max_dd),
                     xytext=(10, -10), textcoords="offset points",
                     fontsize=10, fontweight="bold", color=self.loss_color)
        
        # ドローダウン警告ライン
        ax2.axhline(y=10, color=self._get_color(3), linestyle=":", alpha=0.7, label="10%")
        ax2.axhline(y=20, color=self._get_color(3), linestyle="--", alpha=0.7, label="20%")
        ax2.axhline(y=30, color=self.loss_color, linestyle="-.", alpha=0.7, label="30% (警告)")
        
        self._apply_common_style(ax2,
                                  title="ドローダウン率",
                                  xlabel="レース数",
                                  ylabel="ドローダウン (%)")
        ax2.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        ax2.invert_yaxis()  # Y軸を反転（下が大きいドローダウン）
        
        plt.tight_layout()
        return fig
    
    def _generate_streak(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """連敗/連勝分析グラフ"""
        fig, (ax1, ax2) = self._create_figure(nrows=2, figsize=(12, 10))
        
        # 連敗/連勝を計算
        streaks = []
        current_streak = 0
        streak_type = None  # 'win' or 'loss'
        
        for record in result.bet_history:
            if record.is_hit:
                if streak_type == 'win':
                    current_streak += 1
                else:
                    if streak_type == 'loss':
                        streaks.append(-current_streak)
                    current_streak = 1
                    streak_type = 'win'
            else:
                if streak_type == 'loss':
                    current_streak += 1
                else:
                    if streak_type == 'win':
                        streaks.append(current_streak)
                    current_streak = 1
                    streak_type = 'loss'
        
        # 最後のストリークを追加
        if streak_type == 'win':
            streaks.append(current_streak)
        elif streak_type == 'loss':
            streaks.append(-current_streak)
        
        if not streaks:
            ax1.text(0.5, 0.5, "データなし", transform=ax1.transAxes, ha="center", va="center")
            ax2.text(0.5, 0.5, "データなし", transform=ax2.transAxes, ha="center", va="center")
            return fig
        
        # 上段: ストリーク時系列
        x = range(len(streaks))
        colors = [self.profit_color if s > 0 else self.loss_color for s in streaks]
        ax1.bar(x, streaks, color=colors, alpha=0.8)
        ax1.axhline(y=0, color=self._get_color(6), linestyle="-", linewidth=1)
        
        self._apply_common_style(ax1,
                                  title="連勝/連敗の推移（正: 連勝、負: 連敗）",
                                  xlabel="ストリーク番号",
                                  ylabel="連続数")
        
        # 下段: 連敗/連勝の分布
        win_streaks = [s for s in streaks if s > 0]
        loss_streaks = [-s for s in streaks if s < 0]
        
        bins = range(1, max(max(win_streaks, default=1), max(loss_streaks, default=1)) + 2)
        
        if win_streaks:
            ax2.hist(win_streaks, bins=bins, color=self.profit_color, alpha=0.7, 
                     label=f"連勝 (最大: {max(win_streaks)})", edgecolor="white")
        if loss_streaks:
            ax2.hist(loss_streaks, bins=bins, color=self.loss_color, alpha=0.7, 
                     label=f"連敗 (最大: {max(loss_streaks)})", edgecolor="white")
        
        self._apply_common_style(ax2,
                                  title="連勝/連敗の分布",
                                  xlabel="連続数",
                                  ylabel="頻度")
        ax2.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_volatility(self, result: SimulationResult, window: int = 20, **kwargs) -> plt.Figure:
        """資金変動率グラフ"""
        fig, ax = self._create_figure()
        
        fund_history = result.fund_history
        if len(fund_history) < 2:
            ax.text(0.5, 0.5, "データ不足", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        # リターン率を計算
        returns = []
        for i in range(1, len(fund_history)):
            if fund_history[i - 1] > 0:
                ret = (fund_history[i] - fund_history[i - 1]) / fund_history[i - 1] * 100
            else:
                ret = 0
            returns.append(ret)
        
        # ローリング標準偏差（ボラティリティ）
        volatilities = []
        for i in range(len(returns)):
            start = max(0, i - window + 1)
            window_data = returns[start:i + 1]
            vol = np.std(window_data) if len(window_data) > 1 else 0
            volatilities.append(vol)
        
        x = range(len(volatilities))
        
        ax.plot(x, volatilities, color=self.main_color, linewidth=1.5, label=f"ボラティリティ ({window}期間)")
        ax.fill_between(x, volatilities, 0, color=self.main_color, alpha=0.3)
        
        # 平均ボラティリティ
        mean_vol = np.mean(volatilities)
        ax.axhline(y=mean_vol, color=self._get_color(3), linestyle="--", 
                   label=f"平均: {mean_vol:.2f}%")
        
        self._apply_common_style(ax,
                                  title="資金変動率（ボラティリティ）",
                                  xlabel="レース数",
                                  ylabel="変動率 (%)")
        ax.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_risk_return(self, result: SimulationResult, results: list | None = None, **kwargs) -> plt.Figure:
        """リスク・リターン散布図"""
        fig, ax = self._create_figure()
        
        # 複数の結果がある場合は比較用散布図
        if results:
            for i, res in enumerate(results):
                roi = res.metrics.roi if res.metrics else 0
                dd = res.metrics.max_drawdown if res.metrics else 0
                color = self._get_color(i)
                ax.scatter([dd], [roi], color=color, s=100, label=f"戦略{i+1}")
        else:
            # 単一結果の場合
            roi = result.metrics.roi if result.metrics else 0
            dd = result.metrics.max_drawdown if result.metrics else 0
            ax.scatter([dd], [roi], color=self.main_color, s=150, zorder=5)
            ax.annotate(f"ROI: {roi:.2f}%\nDD: {dd:.2f}%", 
                        xy=(dd, roi), xytext=(10, 10), textcoords="offset points",
                        fontsize=10, fontweight="bold")
        
        # 損益分岐点ライン
        ax.axhline(y=100, color=self._get_color(6), linestyle="--", alpha=0.7, label="損益分岐点")
        
        # 理想ゾーン（高ROI、低ドローダウン）
        ax.fill_between([0, 30], [100, 100], [150, 150], color=self.profit_color, alpha=0.1, label="理想ゾーン")
        
        self._apply_common_style(ax,
                                  title="リスク・リターン分析",
                                  xlabel="最大ドローダウン (%)",
                                  ylabel="ROI (%)")
        ax.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_var(self, result: SimulationResult, confidence: float = 0.95, **kwargs) -> plt.Figure:
        """バリュー・アット・リスク (VaR) グラフ"""
        fig, ax = self._create_figure()
        
        # 個別リターンを計算
        returns = []
        for record in result.bet_history:
            if record.ticket.amount > 0:
                ret = (record.payout - record.ticket.amount) / record.ticket.amount * 100
                returns.append(ret)
        
        if not returns:
            ax.text(0.5, 0.5, "データなし", transform=ax.transAxes, ha="center", va="center")
            return fig
        
        # ヒストグラム
        n, bins, patches = ax.hist(returns, bins=50, color=self.main_color, alpha=0.7, edgecolor="white")
        
        # VaR計算
        var_95 = np.percentile(returns, (1 - confidence) * 100)
        ax.axvline(x=var_95, color=self.loss_color, linestyle="-", linewidth=2, 
                   label=f"VaR {int(confidence*100)}%: {var_95:.2f}%")
        
        # VaR以下を赤で塗りつぶし
        for patch, left_edge in zip(patches, bins[:-1]):
            if left_edge < var_95:
                patch.set_facecolor(self.loss_color)
        
        # 期待損失 (CVaR / Expected Shortfall)
        cvar = np.mean([r for r in returns if r <= var_95])
        ax.axvline(x=cvar, color=self._get_color(5), linestyle="--", linewidth=1.5,
                   label=f"CVaR: {cvar:.2f}%")
        
        self._apply_common_style(ax,
                                  title=f"バリュー・アット・リスク (VaR {int(confidence*100)}%)",
                                  xlabel="リターン (%)",
                                  ylabel="頻度")
        ax.legend(loc="upper right", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def _generate_sharpe(self, result: SimulationResult, window: int = 50, risk_free: float = 0.0, **kwargs) -> plt.Figure:
        """シャープレシオ推移グラフ"""
        fig, ax = self._create_figure()
        
        # リターンを計算
        returns = []
        for record in result.bet_history:
            if record.ticket.amount > 0:
                ret = (record.payout - record.ticket.amount) / record.ticket.amount
                returns.append(ret)
        
        if len(returns) < window:
            ax.text(0.5, 0.5, f"データ不足 (最低{window}件必要)", 
                    transform=ax.transAxes, ha="center", va="center")
            return fig
        
        # ローリングシャープレシオ
        sharpe_ratios = []
        for i in range(window, len(returns) + 1):
            window_data = returns[i - window:i]
            mean_ret = np.mean(window_data)
            std_ret = np.std(window_data, ddof=1)
            if std_ret > 0:
                sharpe = (mean_ret - risk_free) / std_ret
            else:
                sharpe = 0
            sharpe_ratios.append(sharpe)
        
        x = range(window, len(returns) + 1)
        
        ax.plot(x, sharpe_ratios, color=self.main_color, linewidth=1.5)
        
        # ゼロライン
        ax.axhline(y=0, color=self._get_color(6), linestyle="-", linewidth=1, alpha=0.5)
        
        # 良い/悪いゾーン
        ax.axhline(y=1, color=self.profit_color, linestyle="--", alpha=0.7, label="良好 (SR>1)")
        ax.axhline(y=-1, color=self.loss_color, linestyle="--", alpha=0.7, label="悪化 (SR<-1)")
        
        # 最終シャープレシオ
        final_sharpe = sharpe_ratios[-1] if sharpe_ratios else 0
        ax.annotate(f"最終SR: {final_sharpe:.2f}", 
                    xy=(len(returns), final_sharpe),
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=10, fontweight="bold")
        
        self._apply_common_style(ax,
                                  title=f"シャープレシオ推移（{window}期間）",
                                  xlabel="賭け回数",
                                  ylabel="シャープレシオ")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        
        plt.tight_layout()
        return fig
    
    def generate_all(self, result: SimulationResult, output_dir: str = "charts") -> list[str]:
        """全てのリスク分析グラフを生成して保存"""
        from pathlib import Path
        output_path = Path(output_dir)
        
        chart_types = [
            ("drawdown", "risk_drawdown.png"),
            ("streak", "risk_streak.png"),
            ("volatility", "risk_volatility.png"),
            ("risk_return", "risk_return.png"),
            ("var", "risk_var.png"),
            ("sharpe", "risk_sharpe.png"),
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
