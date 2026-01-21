"""資金管理

賭け金の計算と資金管理を行う。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from betting_simulation.models import Ticket


@dataclass
class FundConstraints:
    """資金制約"""
    min_bet: int = 100  # 最小賭け金
    max_bet_per_ticket: int = 100000  # 1馬券あたり最大賭け金
    max_bet_per_race: int = 500000  # 1レースあたり最大賭け金
    max_bet_ratio: float = 0.1  # 資金に対する最大賭け比率
    bet_unit: int = 100  # 賭け金単位
    
    @classmethod
    def from_dict(cls, data: dict) -> "FundConstraints":
        """辞書からFundConstraintsを作成"""
        return cls(
            min_bet=data.get("min_bet", 100),
            max_bet_per_ticket=data.get("max_bet_per_ticket", 100000),
            max_bet_per_race=data.get("max_bet_per_race", 500000),
            max_bet_ratio=data.get("max_bet_ratio", 0.1),
            bet_unit=data.get("bet_unit", 100),
        )


class FundManager(ABC):
    """資金管理の基底クラス"""
    
    name: str = "base"
    description: str = ""
    
    def __init__(
        self, 
        params: dict[str, Any] | None = None,
        constraints: FundConstraints | None = None
    ) -> None:
        """初期化
        
        Args:
            params: 資金管理パラメータ
            constraints: 資金制約
        """
        self.params = params or {}
        self.constraints = constraints or FundConstraints()
        self._current_fund: int = 0
    
    def set_fund(self, fund: int) -> None:
        """現在の資金を設定"""
        self._current_fund = fund
    
    @property
    def current_fund(self) -> int:
        """現在の資金を取得"""
        return self._current_fund
    
    @abstractmethod
    def _calculate_raw_amount(self, ticket: Ticket) -> int:
        """制約適用前の賭け金を計算（サブクラスで実装）"""
        pass
    
    def calculate_bet_amount(self, ticket: Ticket) -> int:
        """制約を適用した賭け金を計算
        
        Args:
            ticket: 馬券
            
        Returns:
            賭け金（円）
        """
        # 基本金額を計算
        raw_amount = self._calculate_raw_amount(ticket)
        
        # 制約を適用
        amount = self._apply_constraints(raw_amount)
        
        return amount
    
    def _apply_constraints(self, amount: int) -> int:
        """制約を適用"""
        c = self.constraints
        
        # 資金不足チェック
        if amount > self._current_fund:
            amount = self._current_fund
        
        # 最大比率チェック
        max_by_ratio = int(self._current_fund * c.max_bet_ratio)
        if amount > max_by_ratio:
            amount = max_by_ratio
        
        # 最大賭け金チェック
        if amount > c.max_bet_per_ticket:
            amount = c.max_bet_per_ticket
        
        # 単位に丸める
        amount = (amount // c.bet_unit) * c.bet_unit
        
        # 最小賭け金チェック
        if amount < c.min_bet:
            return 0
        
        return amount
    
    def calculate_bet_amounts(self, tickets: list[Ticket]) -> list[int]:
        """複数馬券の賭け金を計算（レース単位の制約も考慮）"""
        amounts = []
        total = 0
        
        for ticket in tickets:
            amount = self.calculate_bet_amount(ticket)
            
            # レース単位の制約
            if total + amount > self.constraints.max_bet_per_race:
                amount = max(0, self.constraints.max_bet_per_race - total)
                amount = (amount // self.constraints.bet_unit) * self.constraints.bet_unit
            
            amounts.append(amount)
            total += amount
        
        return amounts


class FixedFundManager(FundManager):
    """固定賭け金方式
    
    毎回同じ金額を賭ける。
    """
    
    name = "fixed"
    description = "毎回固定金額を賭ける"
    
    def _calculate_raw_amount(self, ticket: Ticket) -> int:
        return self.params.get("bet_amount", 1000)


class PercentageFundManager(FundManager):
    """資金比率方式
    
    現在資金の一定割合を賭ける。
    """
    
    name = "percentage"
    description = "現在資金の一定割合を賭ける"
    
    def _calculate_raw_amount(self, ticket: Ticket) -> int:
        percentage = self.params.get("bet_percentage", 0.02)
        return int(self._current_fund * percentage)


class KellyFundManager(FundManager):
    """ケリー基準方式
    
    ケリー基準に基づいて最適な賭け金を計算する。
    """
    
    name = "kelly"
    description = "ケリー基準に基づいて賭ける"
    
    def _calculate_raw_amount(self, ticket: Ticket) -> int:
        kelly_fraction = self.params.get("kelly_fraction", 0.25)  # 1/4 Kelly
        
        # 期待値から勝率を推定
        # expected_value = win_prob * odds
        # win_prob = expected_value / odds
        if ticket.odds <= 0:
            return 0
        
        win_prob = ticket.expected_value / ticket.odds if ticket.odds > 0 else 0
        
        # 勝率が0以下または1以上なら賭けない
        if win_prob <= 0 or win_prob >= 1:
            return 0
        
        # ケリー基準: f* = (bp - q) / b
        # b = オッズ - 1 (払戻倍率)
        # p = 勝率
        # q = 1 - p (敗率)
        b = ticket.odds - 1
        p = win_prob
        q = 1 - p
        
        kelly = (b * p - q) / b if b > 0 else 0
        
        # 負の場合は賭けない
        if kelly <= 0:
            return 0
        
        # kelly_fraction を適用
        kelly *= kelly_fraction
        
        # 資金に対する金額を計算
        amount = int(self._current_fund * kelly)
        
        return amount


class FundManagerFactory:
    """資金管理ファクトリー"""
    
    _managers: dict[str, type[FundManager]] = {
        "fixed": FixedFundManager,
        "percentage": PercentageFundManager,
        "kelly": KellyFundManager,
    }
    
    @classmethod
    def create(
        cls, 
        name: str, 
        params: dict[str, Any] | None = None,
        constraints: FundConstraints | None = None
    ) -> FundManager:
        """資金管理インスタンスを作成
        
        Args:
            name: 資金管理方式名
            params: パラメータ
            constraints: 制約
            
        Returns:
            FundManagerインスタンス
        """
        if name not in cls._managers:
            raise ValueError(f"Unknown fund manager: {name}. Available: {list(cls._managers.keys())}")
        
        return cls._managers[name](params, constraints)
    
    @classmethod
    def list_managers(cls) -> list[dict[str, str]]:
        """利用可能な資金管理方式一覧"""
        return [
            {"name": name, "description": manager.description}
            for name, manager in cls._managers.items()
        ]
