"""データモデル定義

競馬賭けシミュレーションで使用するデータ構造を定義する。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TicketType(Enum):
    """馬券種別"""
    WIN = "単勝"
    PLACE = "複勝"
    QUINELLA = "馬連"
    WIDE = "ワイド"
    TRIO = "三連複"
    
    def __str__(self) -> str:
        return self.value


class Surface(Enum):
    """コース種別"""
    TURF = "芝"
    DIRT = "ダート"
    
    @classmethod
    def from_str(cls, value: str) -> "Surface":
        """文字列からSurfaceを生成"""
        if value == "芝":
            return cls.TURF
        elif value in ("ダート", "ダ"):
            return cls.DIRT
        else:
            raise ValueError(f"Unknown surface: {value}")


@dataclass
class Horse:
    """馬データ"""
    number: int  # 馬番
    name: str  # 馬名
    odds: float  # 単勝オッズ
    popularity: int  # 人気順
    actual_rank: int  # 確定着順
    predicted_rank: int  # 予測順位
    predicted_score: float  # 予測スコア
    
    # オプション項目
    hole_probability: float = 0.0  # 穴馬確率
    is_hole_candidate: bool = False  # 穴馬候補フラグ
    is_actual_hole: bool = False  # 実際の穴馬フラグ
    
    def __post_init__(self) -> None:
        """バリデーション"""
        if self.number < 1:
            raise ValueError(f"Invalid horse number: {self.number}")
        if self.odds < 1.0:
            raise ValueError(f"Invalid odds: {self.odds}")


@dataclass
class RacePayouts:
    """レース払戻情報"""
    # 単勝
    win_horse: int = 0
    win_payout: float = 0.0
    
    # 複勝（3着まで）
    place_horses: list[int] = field(default_factory=list)
    place_payouts: list[float] = field(default_factory=list)
    place_popularities: list[int] = field(default_factory=list)
    
    # 馬連
    quinella_horses: tuple[int, int] = (0, 0)
    quinella_payout: float = 0.0
    
    # ワイド（3通り）
    wide_pairs: list[tuple[int, int]] = field(default_factory=list)
    wide_payouts: list[float] = field(default_factory=list)
    
    # 馬単
    exacta_horses: tuple[int, int] = (0, 0)
    exacta_payout: float = 0.0
    
    # 三連複
    trio_horses: tuple[int, int, int] = (0, 0, 0)
    trio_payout: float = 0.0


@dataclass
class Race:
    """レースデータ"""
    track: str  # 競馬場
    year: int  # 開催年
    kaisai_date: int  # 開催日（MMDD形式）
    race_number: int  # レース番号
    surface: Surface  # 芝/ダート
    distance: int  # 距離
    horses: list[Horse] = field(default_factory=list)
    payouts: Optional[RacePayouts] = None
    
    @property
    def race_id(self) -> str:
        """レース一意識別子"""
        return f"{self.track}_{self.year}_{self.kaisai_date:04d}_{self.race_number:02d}"
    
    @property
    def num_horses(self) -> int:
        """出走頭数"""
        return len(self.horses)
    
    def get_horse_by_number(self, number: int) -> Optional[Horse]:
        """馬番から馬を取得"""
        for horse in self.horses:
            if horse.number == number:
                return horse
        return None
    
    def get_top_predicted(self, n: int = 1) -> list[Horse]:
        """予測上位n頭を取得"""
        sorted_horses = sorted(self.horses, key=lambda h: h.predicted_rank)
        return sorted_horses[:n]
    
    def get_top_by_odds(self, n: int = 1) -> list[Horse]:
        """オッズ上位（低オッズ）n頭を取得"""
        sorted_horses = sorted(self.horses, key=lambda h: h.odds)
        return sorted_horses[:n]
    
    def get_top_by_popularity(self, n: int = 1) -> list[Horse]:
        """人気上位n頭を取得"""
        sorted_horses = sorted(self.horses, key=lambda h: h.popularity)
        return sorted_horses[:n]
    
    def get_actual_top(self, n: int = 3) -> list[Horse]:
        """実際の着順上位n頭を取得"""
        sorted_horses = sorted(self.horses, key=lambda h: h.actual_rank)
        return sorted_horses[:n]


@dataclass
class Ticket:
    """馬券"""
    ticket_type: TicketType  # 馬券種別
    horse_numbers: tuple[int, ...]  # 馬番（単勝/複勝は1つ、馬連は2つ等）
    amount: int = 0  # 賭け金（円）
    odds: float = 0.0  # オッズ（単勝/複勝のみ）
    expected_value: float = 0.0  # 期待値
    
    @property
    def numbers_str(self) -> str:
        """馬番の文字列表現"""
        return "-".join(map(str, sorted(self.horse_numbers)))
    
    def __str__(self) -> str:
        return f"{self.ticket_type}[{self.numbers_str}] {self.amount}円"


@dataclass
class BetRecord:
    """賭け記録"""
    race: Race
    ticket: Ticket
    is_hit: bool  # 的中フラグ
    payout: int  # 払戻金
    fund_before: int  # 賭け前資金
    fund_after: int  # 賭け後資金
    
    @property
    def profit(self) -> int:
        """損益"""
        return self.payout - self.ticket.amount
    
    @property
    def roi(self) -> float:
        """個別ROI（%）"""
        if self.ticket.amount == 0:
            return 0.0
        return (self.payout / self.ticket.amount) * 100


@dataclass
class SimulationMetrics:
    """シミュレーション評価指標"""
    total_races: int = 0  # 総レース数
    total_bets: int = 0  # 総賭け回数
    total_hits: int = 0  # 的中回数
    total_invested: int = 0  # 総投資額
    total_payout: int = 0  # 総払戻額
    
    # 計算指標
    hit_rate: float = 0.0  # 的中率（%）
    roi: float = 0.0  # ROI（%）
    profit: int = 0  # 純利益
    max_drawdown: float = 0.0  # 最大ドローダウン（%）
    max_drawdown_period: int = 0  # 最大DD期間
    sharpe_ratio: float = 0.0  # シャープレシオ
    max_consecutive_losses: int = 0  # 最大連敗数
    max_consecutive_wins: int = 0  # 最大連勝数
    
    # Go/No-Go判定
    is_go: bool = False  # Go判定


@dataclass
class SimulationResult:
    """シミュレーション結果"""
    initial_fund: int
    final_fund: int
    bet_history: list[BetRecord] = field(default_factory=list)
    fund_history: list[int] = field(default_factory=list)
    metrics: Optional[SimulationMetrics] = None
    
    @property
    def profit(self) -> int:
        """純利益"""
        return self.final_fund - self.initial_fund
    
    @property
    def roi(self) -> float:
        """ROI（%）"""
        if self.initial_fund == 0:
            return 0.0
        return (self.final_fund / self.initial_fund) * 100


@dataclass 
class MonteCarloResult:
    """モンテカルロシミュレーション結果"""
    num_trials: int
    final_funds: list[int] = field(default_factory=list)
    
    # 統計値
    mean_final_fund: float = 0.0
    median_final_fund: float = 0.0
    std_final_fund: float = 0.0
    min_final_fund: int = 0
    max_final_fund: int = 0
    
    # パーセンタイル
    percentile_5: float = 0.0
    percentile_25: float = 0.0
    percentile_75: float = 0.0
    percentile_95: float = 0.0
    
    # 破産確率
    bankruptcy_rate: float = 0.0  # 資金が一定以下になる確率
    profit_rate: float = 0.0  # 利益が出る確率
