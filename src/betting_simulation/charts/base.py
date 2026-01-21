"""チャート生成の基盤クラス

全てのチャートジェネレーターの基底クラスと共通設定を定義。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np


@dataclass
class ChartConfig:
    """チャート設定"""
    # サイズ
    figsize: tuple[int, int] = (12, 8)
    dpi: int = 100
    
    # スタイル
    style: str = "seaborn-v0_8-whitegrid"
    color_palette: list[str] = field(default_factory=lambda: [
        "#2ecc71",  # 緑（利益）
        "#e74c3c",  # 赤（損失）
        "#3498db",  # 青（メイン）
        "#f39c12",  # オレンジ
        "#9b59b6",  # 紫
        "#1abc9c",  # ティール
        "#34495e",  # グレー
        "#e67e22",  # ダークオレンジ
    ])
    
    # フォント
    font_family: str = "sans-serif"
    title_fontsize: int = 14
    label_fontsize: int = 12
    tick_fontsize: int = 10
    legend_fontsize: int = 10
    
    # グリッド
    show_grid: bool = True
    grid_alpha: float = 0.3
    
    # 出力
    output_format: str = "png"
    transparent: bool = False
    
    # 日本語フォント（Windowsの場合）
    japanese_font: str = "Yu Gothic"


class ChartGenerator(ABC):
    """チャートジェネレーター基底クラス"""
    
    def __init__(self, config: ChartConfig | None = None) -> None:
        """初期化
        
        Args:
            config: チャート設定（省略時はデフォルト）
        """
        self.config = config or ChartConfig()
        self._setup_style()
    
    def _setup_style(self) -> None:
        """Matplotlibスタイルを設定"""
        try:
            plt.style.use(self.config.style)
        except OSError:
            # スタイルが見つからない場合はデフォルトを使用
            plt.style.use("default")
        
        # 日本語フォント設定
        plt.rcParams["font.family"] = self.config.font_family
        plt.rcParams["font.size"] = self.config.label_fontsize
        
        # 日本語フォントが利用可能か確認
        try:
            font_path = fm.findfont(fm.FontProperties(family=self.config.japanese_font))
            if font_path:
                plt.rcParams["font.sans-serif"] = [self.config.japanese_font, "DejaVu Sans"]
        except Exception:
            pass
        
        # マイナス記号の文字化け対策
        plt.rcParams["axes.unicode_minus"] = False
    
    def _create_figure(
        self, 
        figsize: tuple[int, int] | None = None,
        nrows: int = 1,
        ncols: int = 1,
        **kwargs
    ) -> tuple[plt.Figure, Any]:
        """Figure/Axesを作成
        
        Args:
            figsize: 図のサイズ（省略時はconfig値）
            nrows: 行数
            ncols: 列数
            **kwargs: subplot用の追加引数
            
        Returns:
            (Figure, Axes)のタプル
        """
        figsize = figsize or self.config.figsize
        fig, axes = plt.subplots(nrows, ncols, figsize=figsize, dpi=self.config.dpi, **kwargs)
        return fig, axes
    
    def _apply_common_style(self, ax: plt.Axes, title: str = "", xlabel: str = "", ylabel: str = "") -> None:
        """共通スタイルを適用
        
        Args:
            ax: Axes
            title: タイトル
            xlabel: X軸ラベル
            ylabel: Y軸ラベル
        """
        if title:
            ax.set_title(title, fontsize=self.config.title_fontsize, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self.config.label_fontsize)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self.config.label_fontsize)
        
        ax.tick_params(labelsize=self.config.tick_fontsize)
        
        if self.config.show_grid:
            ax.grid(True, alpha=self.config.grid_alpha)
    
    def _get_color(self, index: int) -> str:
        """カラーパレットから色を取得"""
        return self.config.color_palette[index % len(self.config.color_palette)]
    
    @property
    def profit_color(self) -> str:
        """利益の色（緑）"""
        return self.config.color_palette[0]
    
    @property
    def loss_color(self) -> str:
        """損失の色（赤）"""
        return self.config.color_palette[1]
    
    @property
    def main_color(self) -> str:
        """メインカラー（青）"""
        return self.config.color_palette[2]
    
    def save(self, fig: plt.Figure, filepath: str | Path, **kwargs) -> Path:
        """チャートを保存
        
        Args:
            fig: Figure
            filepath: 保存先パス
            **kwargs: savefig用の追加引数
            
        Returns:
            保存したファイルパス
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        save_kwargs = {
            "dpi": self.config.dpi,
            "transparent": self.config.transparent,
            "bbox_inches": "tight",
        }
        save_kwargs.update(kwargs)
        
        fig.savefig(filepath, **save_kwargs)
        plt.close(fig)
        
        return filepath
    
    def show(self, fig: plt.Figure) -> None:
        """チャートを表示"""
        plt.show()
    
    @abstractmethod
    def generate(self, *args, **kwargs) -> plt.Figure:
        """チャートを生成（サブクラスで実装）"""
        pass


def format_currency(value: float, prefix: str = "¥") -> str:
    """通貨フォーマット
    
    Args:
        value: 金額
        prefix: 通貨記号
        
    Returns:
        フォーマット済み文字列
    """
    if value >= 0:
        return f"{prefix}{value:,.0f}"
    else:
        return f"-{prefix}{abs(value):,.0f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """パーセントフォーマット
    
    Args:
        value: パーセント値
        decimals: 小数点以下桁数
        
    Returns:
        フォーマット済み文字列
    """
    return f"{value:.{decimals}f}%"


def calculate_moving_average(data: list[float], window: int = 10) -> np.ndarray:
    """移動平均を計算
    
    Args:
        data: データ列
        window: ウィンドウサイズ
        
    Returns:
        移動平均配列
    """
    data_array = np.array(data)
    if len(data_array) < window:
        return data_array
    
    cumsum = np.cumsum(np.insert(data_array, 0, 0))
    ma = (cumsum[window:] - cumsum[:-window]) / window
    
    # 先頭のNaN部分を埋める
    result = np.full(len(data_array), np.nan)
    result[window - 1:] = ma
    
    return result
