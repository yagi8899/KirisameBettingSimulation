"""資金推移グラフ（6種）

1. 資金推移（基本）
2. 資金推移（移動平均付き）
3. 資金推移（目標ライン付き）
4. 資金推移（最高/最低ライン付き）
5. 日別収支グラフ
6. 累積収支グラフ
"""

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from betting_simulation.charts.base import (
    ChartGenerator, ChartConfig, format_currency, calculate_moving_average
)
from betting_simulation.models import SimulationResult


class FundChartGenerator(ChartGenerator):
    """資金推移グラフジェネレーター"""
    
    def generate(self, result: SimulationResult, chart_type: str = "basic", **kwargs) -> plt.Figure:
        """資金推移グラフを生成
        
        Args:
            result: シミュレーション結果
            chart_type: グラフ種別
                - "basic": 基本
                - "with_ma": 移動平均付き
                - "with_target": 目標ライン付き
                - "with_minmax": 最高/最低ライン付き
                - "daily": 日別収支
                - "cumulative": 累積収支
            **kwargs: 追加オプション
            
        Returns:
            Figure
        """
        methods = {
            "basic": self._generate_basic,
            "with_ma": self._generate_with_ma,
            "with_target": self._generate_with_target,
            "with_minmax": self._generate_with_minmax,
            "daily": self._generate_daily,
            "cumulative": self._generate_cumulative,
        }
        
        method = methods.get(chart_type)
        if method is None:
            raise ValueError(f"Unknown chart type: {chart_type}")
        
        return method(result, **kwargs)
    
    def _generate_basic(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """基本的な資金推移グラフ"""
        fig, ax = self._create_figure()
        
        fund_history = result.fund_history
        x = range(len(fund_history))
        
        # 資金推移ライン
        ax.plot(x, fund_history, color=self.main_color, linewidth=2, label="資金")
        
        # 初期資金ライン
        ax.axhline(y=result.initial_fund, color=self._get_color(6), 
                   linestyle="--", alpha=0.7, label=f"初期資金 ({format_currency(result.initial_fund)})")
        
        # 資金が初期値を上回っている部分を緑、下回っている部分を赤で塗りつぶし
        ax.fill_between(x, fund_history, result.initial_fund,
                        where=[f >= result.initial_fund for f in fund_history],
                        color=self.profit_color, alpha=0.3)
        ax.fill_between(x, fund_history, result.initial_fund,
                        where=[f < result.initial_fund for f in fund_history],
                        color=self.loss_color, alpha=0.3)
        
        self._apply_common_style(ax, 
                                  title="資金推移",
                                  xlabel="レース数",
                                  ylabel="資金 (円)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        
        # Y軸のフォーマット
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_with_ma(self, result: SimulationResult, window: int = 20, **kwargs) -> plt.Figure:
        """移動平均付き資金推移グラフ"""
        fig, ax = self._create_figure()
        
        fund_history = result.fund_history
        x = range(len(fund_history))
        
        # 資金推移ライン
        ax.plot(x, fund_history, color=self.main_color, linewidth=1.5, alpha=0.7, label="資金")
        
        # 移動平均
        ma = calculate_moving_average(fund_history, window)
        ax.plot(x, ma, color=self._get_color(3), linewidth=2, label=f"移動平均 ({window})")
        
        # 初期資金ライン
        ax.axhline(y=result.initial_fund, color=self._get_color(6), 
                   linestyle="--", alpha=0.5, label="初期資金")
        
        self._apply_common_style(ax,
                                  title=f"資金推移（{window}期間移動平均）",
                                  xlabel="レース数",
                                  ylabel="資金 (円)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_with_target(self, result: SimulationResult, target: int | None = None, **kwargs) -> plt.Figure:
        """目標ライン付き資金推移グラフ"""
        fig, ax = self._create_figure()
        
        fund_history = result.fund_history
        x = range(len(fund_history))
        
        # デフォルト目標は初期資金の150%
        target = target or int(result.initial_fund * 1.5)
        
        # 資金推移ライン
        ax.plot(x, fund_history, color=self.main_color, linewidth=2, label="資金")
        
        # 初期資金ライン
        ax.axhline(y=result.initial_fund, color=self._get_color(6), 
                   linestyle="--", alpha=0.5, label="初期資金")
        
        # 目標ライン
        ax.axhline(y=target, color=self.profit_color, 
                   linestyle="-.", linewidth=2, alpha=0.8, 
                   label=f"目標 ({format_currency(target)})")
        
        # 損切りライン（初期資金の50%）
        stop_loss = int(result.initial_fund * 0.5)
        ax.axhline(y=stop_loss, color=self.loss_color, 
                   linestyle="-.", linewidth=2, alpha=0.8,
                   label=f"損切り ({format_currency(stop_loss)})")
        
        self._apply_common_style(ax,
                                  title="資金推移（目標/損切りライン）",
                                  xlabel="レース数",
                                  ylabel="資金 (円)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_with_minmax(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """最高/最低ライン付き資金推移グラフ"""
        fig, ax = self._create_figure()
        
        fund_history = result.fund_history
        x = range(len(fund_history))
        
        max_fund = max(fund_history)
        min_fund = min(fund_history)
        max_idx = fund_history.index(max_fund)
        min_idx = fund_history.index(min_fund)
        
        # 資金推移ライン
        ax.plot(x, fund_history, color=self.main_color, linewidth=2, label="資金")
        
        # 最高点マーカー
        ax.scatter([max_idx], [max_fund], color=self.profit_color, s=100, zorder=5,
                   label=f"最高 ({format_currency(max_fund)})")
        
        # 最低点マーカー
        ax.scatter([min_idx], [min_fund], color=self.loss_color, s=100, zorder=5,
                   label=f"最低 ({format_currency(min_fund)})")
        
        # 最高/最低ライン
        ax.axhline(y=max_fund, color=self.profit_color, linestyle=":", alpha=0.5)
        ax.axhline(y=min_fund, color=self.loss_color, linestyle=":", alpha=0.5)
        
        # 初期資金ライン
        ax.axhline(y=result.initial_fund, color=self._get_color(6), 
                   linestyle="--", alpha=0.5, label="初期資金")
        
        self._apply_common_style(ax,
                                  title="資金推移（最高/最低）",
                                  xlabel="レース数",
                                  ylabel="資金 (円)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_daily(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """日別収支グラフ"""
        fig, ax = self._create_figure()
        
        # 賭け履歴から日別収支を計算
        daily_profits = {}
        for record in result.bet_history:
            race_id = record.race.race_id
            # race_idから日付を抽出（形式: track_year_MMDD_racenum）
            parts = race_id.split("_")
            if len(parts) >= 3:
                date_key = f"{parts[1]}/{parts[2]}"
            else:
                date_key = race_id
            
            if date_key not in daily_profits:
                daily_profits[date_key] = 0
            daily_profits[date_key] += record.profit
        
        if not daily_profits:
            # データがない場合は資金変動から推定
            ax.text(0.5, 0.5, "日別データなし", transform=ax.transAxes,
                    ha="center", va="center", fontsize=14)
            return fig
        
        dates = list(daily_profits.keys())
        profits = list(daily_profits.values())
        
        colors = [self.profit_color if p >= 0 else self.loss_color for p in profits]
        
        ax.bar(range(len(dates)), profits, color=colors, alpha=0.8)
        ax.axhline(y=0, color=self._get_color(6), linestyle="-", linewidth=1)
        
        # X軸ラベルを間引いて表示
        if len(dates) > 20:
            step = len(dates) // 10
            ax.set_xticks(range(0, len(dates), step))
            ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45)
        else:
            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels(dates, rotation=45)
        
        self._apply_common_style(ax,
                                  title="日別収支",
                                  xlabel="日付",
                                  ylabel="収支 (円)")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def _generate_cumulative(self, result: SimulationResult, **kwargs) -> plt.Figure:
        """累積収支グラフ"""
        fig, ax = self._create_figure()
        
        fund_history = result.fund_history
        # 累積収支 = 現在資金 - 初期資金
        cumulative_profits = [f - result.initial_fund for f in fund_history]
        x = range(len(cumulative_profits))
        
        # 累積収支ライン
        ax.plot(x, cumulative_profits, color=self.main_color, linewidth=2, label="累積収支")
        
        # 0ライン
        ax.axhline(y=0, color=self._get_color(6), linestyle="--", alpha=0.7)
        
        # 利益/損失の塗りつぶし
        ax.fill_between(x, cumulative_profits, 0,
                        where=[p >= 0 for p in cumulative_profits],
                        color=self.profit_color, alpha=0.3, label="利益")
        ax.fill_between(x, cumulative_profits, 0,
                        where=[p < 0 for p in cumulative_profits],
                        color=self.loss_color, alpha=0.3, label="損失")
        
        # 最終損益を表示
        final_profit = cumulative_profits[-1] if cumulative_profits else 0
        profit_text = format_currency(final_profit)
        color = self.profit_color if final_profit >= 0 else self.loss_color
        ax.annotate(f"最終: {profit_text}", 
                    xy=(len(cumulative_profits) - 1, final_profit),
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=12, color=color, fontweight="bold")
        
        self._apply_common_style(ax,
                                  title="累積収支推移",
                                  xlabel="レース数",
                                  ylabel="累積収支 (円)")
        ax.legend(loc="upper left", fontsize=self.config.legend_fontsize)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format_currency(x)))
        
        plt.tight_layout()
        return fig
    
    def generate_all(self, result: SimulationResult, output_dir: str = "charts") -> list[str]:
        """全ての資金推移グラフを生成して保存
        
        Args:
            result: シミュレーション結果
            output_dir: 出力ディレクトリ
            
        Returns:
            保存したファイルパスのリスト
        """
        from pathlib import Path
        output_path = Path(output_dir)
        
        chart_types = [
            ("basic", "fund_basic.png"),
            ("with_ma", "fund_with_ma.png"),
            ("with_target", "fund_with_target.png"),
            ("with_minmax", "fund_with_minmax.png"),
            ("daily", "fund_daily.png"),
            ("cumulative", "fund_cumulative.png"),
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
