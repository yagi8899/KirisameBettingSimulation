"""賭け戦略

各種賭け戦略を定義する。
"""

from abc import ABC, abstractmethod
from itertools import combinations
from typing import Any

from betting_simulation.models import Horse, Race, Ticket, TicketType


class Strategy(ABC):
    """戦略の基底クラス"""
    
    name: str = "base"
    description: str = ""
    
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        """初期化
        
        Args:
            params: 戦略パラメータ
        """
        self.params = params or {}
    
    @abstractmethod
    def generate_tickets(self, race: Race) -> list[Ticket]:
        """馬券を生成
        
        Args:
            race: レースデータ
            
        Returns:
            生成した馬券リスト
        """
        pass
    
    def _get_param(self, key: str, default: Any = None) -> Any:
        """パラメータを取得"""
        return self.params.get(key, default)


# =============================================================================
# 単勝戦略
# =============================================================================

class FavoriteWinStrategy(Strategy):
    """予測上位単勝戦略
    
    予測順位上位N頭の単勝馬券を購入する。
    """
    
    name = "favorite_win"
    description = "予測上位N頭の単勝を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        top_n = self._get_param("top_n", 1)
        min_odds = self._get_param("min_odds", 1.0)
        max_odds = self._get_param("max_odds", 999.0)
        
        top_horses = race.get_top_predicted_safe(top_n)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        for horse in top_horses:
            if min_odds <= horse.odds <= max_odds:
                ticket = Ticket(
                    ticket_type=TicketType.WIN,
                    horse_numbers=(horse.number,),
                    odds=horse.odds,
                    expected_value=horse.predicted_score * horse.odds
                )
                tickets.append(ticket)
        
        return tickets


class PopularityWinStrategy(Strategy):
    """人気順単勝戦略
    
    人気順上位N頭の単勝馬券を購入する。
    """
    
    name = "popularity_win"
    description = "人気上位N頭の単勝を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        top_n = self._get_param("top_n", 1)
        min_odds = self._get_param("min_odds", 1.0)
        max_odds = self._get_param("max_odds", 999.0)
        
        tickets = []
        top_horses = race.get_top_by_popularity(top_n)
        
        for horse in top_horses:
            if min_odds <= horse.odds <= max_odds:
                ticket = Ticket(
                    ticket_type=TicketType.WIN,
                    horse_numbers=(horse.number,),
                    odds=horse.odds,
                    expected_value=horse.predicted_score * horse.odds
                )
                tickets.append(ticket)
        
        return tickets


class ValueWinStrategy(Strategy):
    """期待値ベース単勝戦略
    
    期待値が閾値以上の馬の単勝を購入する。
    """
    
    name = "value_win"
    description = "期待値が閾値以上の馬の単勝を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        min_expected_value = self._get_param("min_expected_value", 1.0)
        max_tickets = self._get_param("max_tickets", 3)
        
        tickets = []
        
        # 期待値でソート
        horses_with_ev = [
            (h, h.predicted_score * h.odds) 
            for h in race.horses
        ]
        horses_with_ev.sort(key=lambda x: x[1], reverse=True)
        
        for horse, ev in horses_with_ev:
            if ev >= min_expected_value and len(tickets) < max_tickets:
                ticket = Ticket(
                    ticket_type=TicketType.WIN,
                    horse_numbers=(horse.number,),
                    odds=horse.odds,
                    expected_value=ev
                )
                tickets.append(ticket)
        
        return tickets


# =============================================================================
# 複勝戦略
# =============================================================================

class FavoritePlaceStrategy(Strategy):
    """予測上位複勝戦略
    
    予測順位上位N頭の複勝馬券を購入する。
    """
    
    name = "favorite_place"
    description = "予測上位N頭の複勝を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        top_n = self._get_param("top_n", 1)
        
        top_horses = race.get_top_predicted_safe(top_n)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        for horse in top_horses:
            # 複勝オッズは単勝の約1/3と仮定（実際の払戻は別途計算）
            estimated_odds = max(1.1, horse.odds / 3)
            ticket = Ticket(
                ticket_type=TicketType.PLACE,
                horse_numbers=(horse.number,),
                odds=estimated_odds,
                expected_value=horse.predicted_score * estimated_odds * 3  # 3着以内確率
            )
            tickets.append(ticket)
        
        return tickets


# =============================================================================
# 馬連戦略
# =============================================================================

class BoxQuinellaStrategy(Strategy):
    """ボックス馬連戦略
    
    予測上位N頭のボックス馬連を購入する。
    """
    
    name = "box_quinella"
    description = "予測上位N頭のボックス馬連を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        box_size = self._get_param("box_size", 4)
        
        top_horses = race.get_top_predicted_safe(box_size)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        if len(top_horses) < 2:
            return []
        
        # 全組み合わせ
        for h1, h2 in combinations(top_horses, 2):
            ticket = Ticket(
                ticket_type=TicketType.QUINELLA,
                horse_numbers=(h1.number, h2.number),
                odds=0,  # 馬連オッズは払戻時に参照
            )
            tickets.append(ticket)
        
        return tickets


class FlowQuinellaStrategy(Strategy):
    """流し馬連戦略
    
    軸馬から相手馬への流し馬連を購入する。
    """
    
    name = "flow_quinella"
    description = "軸馬から相手馬への流し馬連を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        num_axis = self._get_param("num_axis", 1)  # 軸馬数
        num_partners = self._get_param("num_partners", 5)  # 相手馬数
        
        top_horses = race.get_top_predicted_safe(num_axis + num_partners)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        if len(top_horses) < 2:
            return []
        
        axis_horses = top_horses[:num_axis]
        partner_horses = top_horses[num_axis:num_axis + num_partners]
        
        for axis in axis_horses:
            for partner in partner_horses:
                ticket = Ticket(
                    ticket_type=TicketType.QUINELLA,
                    horse_numbers=(axis.number, partner.number),
                )
                tickets.append(ticket)
        
        return tickets


# =============================================================================
# ワイド戦略
# =============================================================================

class BoxWideStrategy(Strategy):
    """ボックスワイド戦略
    
    予測上位N頭のボックスワイドを購入する。
    """
    
    name = "box_wide"
    description = "予測上位N頭のボックスワイドを購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        box_size = self._get_param("box_size", 4)
        
        top_horses = race.get_top_predicted_safe(box_size)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        if len(top_horses) < 2:
            return []
        
        for h1, h2 in combinations(top_horses, 2):
            ticket = Ticket(
                ticket_type=TicketType.WIDE,
                horse_numbers=(h1.number, h2.number),
            )
            tickets.append(ticket)
        
        return tickets


# =============================================================================
# 三連複戦略
# =============================================================================

class BoxTrioStrategy(Strategy):
    """ボックス三連複戦略
    
    予測上位N頭のボックス三連複を購入する。
    """
    
    name = "box_trio"
    description = "予測上位N頭のボックス三連複を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        box_size = self._get_param("box_size", 5)
        
        top_horses = race.get_top_predicted_safe(box_size)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        if len(top_horses) < 3:
            return []
        
        for h1, h2, h3 in combinations(top_horses, 3):
            ticket = Ticket(
                ticket_type=TicketType.TRIO,
                horse_numbers=(h1.number, h2.number, h3.number),
            )
            tickets.append(ticket)
        
        return tickets


class FlowTrioStrategy(Strategy):
    """流し三連複戦略
    
    軸馬から相手馬への流し三連複を購入する。
    """
    
    name = "flow_trio"
    description = "1頭軸流し三連複を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        num_partners = self._get_param("num_partners", 6)
        
        top_horses = race.get_top_predicted_safe(1 + num_partners)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        if len(top_horses) < 3:
            return []
        
        axis = top_horses[0]
        partners = top_horses[1:1 + num_partners]
        
        # 軸1頭 + 相手2頭の組み合わせ
        for p1, p2 in combinations(partners, 2):
            ticket = Ticket(
                ticket_type=TicketType.TRIO,
                horse_numbers=(axis.number, p1.number, p2.number),
            )
            tickets.append(ticket)
        
        return tickets


class WheelQuinellaStrategy(Strategy):
    """ホイール馬連戦略
    
    軸馬1頭から全相手馬への馬連を購入する。
    """
    
    name = "wheel_quinella"
    description = "軸馬1頭から相手全頭への馬連を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        num_axis = self._get_param("num_axis", 1)
        exclude_low_odds = self._get_param("exclude_low_odds", 0)  # 除外する低オッズ馬数
        
        top_horses = race.get_top_predicted_safe(num_axis)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        if not top_horses:
            return []
        
        # 相手馬（軸馬以外の全馬）
        axis_numbers = {h.number for h in top_horses}
        partners = [h for h in race.horses if h.number not in axis_numbers]
        
        # 低オッズ馬を除外
        if exclude_low_odds > 0:
            partners = sorted(partners, key=lambda h: h.odds)[exclude_low_odds:]
        
        for axis in top_horses:
            for partner in partners:
                ticket = Ticket(
                    ticket_type=TicketType.QUINELLA,
                    horse_numbers=(axis.number, partner.number),
                )
                tickets.append(ticket)
        
        return tickets


class FormationTrioStrategy(Strategy):
    """フォーメーション三連複戦略
    
    1列目、2列目、3列目を指定して三連複を購入する。
    """
    
    name = "formation_trio"
    description = "フォーメーション三連複を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        first_n = self._get_param("first_n", 2)  # 1列目の頭数
        second_n = self._get_param("second_n", 4)  # 2列目の頭数
        third_n = self._get_param("third_n", 6)  # 3列目の頭数
        
        max_n = max(first_n, second_n, third_n)
        top_horses = race.get_top_predicted_safe(max_n)
        if top_horses is None:
            return []  # 予測順位に重複があるためスキップ
        
        tickets = []
        if len(top_horses) < 3:
            return []
        
        first = [h.number for h in top_horses[:first_n]]
        second = [h.number for h in top_horses[:second_n]]
        third = [h.number for h in top_horses[:third_n]]
        
        # 全組み合わせを生成（重複除去）
        seen = set()
        for h1 in first:
            for h2 in second:
                for h3 in third:
                    if h1 != h2 and h2 != h3 and h1 != h3:
                        combo = tuple(sorted([h1, h2, h3]))
                        if combo not in seen:
                            seen.add(combo)
                            ticket = Ticket(
                                ticket_type=TicketType.TRIO,
                                horse_numbers=combo,
                            )
                            tickets.append(ticket)
        
        return tickets


# =============================================================================
# 穴馬戦略
# =============================================================================

class HoleHorseWinStrategy(Strategy):
    """穴馬単勝戦略
    
    穴馬確率が高い馬の単勝を購入する。
    """
    
    name = "hole_win"
    description = "穴馬確率が高い馬の単勝を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        min_hole_prob = self._get_param("min_hole_probability", 0.3)
        max_tickets = self._get_param("max_tickets", 2)
        min_odds = self._get_param("min_odds", 5.0)
        
        tickets = []
        
        # 穴馬確率でソート
        candidates = [h for h in race.horses 
                      if h.hole_probability >= min_hole_prob and h.odds >= min_odds]
        candidates.sort(key=lambda h: h.hole_probability, reverse=True)
        
        for horse in candidates[:max_tickets]:
            ticket = Ticket(
                ticket_type=TicketType.WIN,
                horse_numbers=(horse.number,),
                odds=horse.odds,
                expected_value=horse.hole_probability * horse.odds
            )
            tickets.append(ticket)
        
        return tickets


class HoleHorsePlaceStrategy(Strategy):
    """穴馬複勝戦略
    
    穴馬確率が高い馬の複勝を購入する。
    """
    
    name = "hole_place"
    description = "穴馬確率が高い馬の複勝を購入"
    
    def generate_tickets(self, race: Race) -> list[Ticket]:
        min_hole_prob = self._get_param("min_hole_probability", 0.2)
        max_tickets = self._get_param("max_tickets", 3)
        
        tickets = []
        
        candidates = [h for h in race.horses if h.hole_probability >= min_hole_prob]
        candidates.sort(key=lambda h: h.hole_probability, reverse=True)
        
        for horse in candidates[:max_tickets]:
            estimated_odds = max(1.1, horse.odds / 3)
            ticket = Ticket(
                ticket_type=TicketType.PLACE,
                horse_numbers=(horse.number,),
                odds=estimated_odds,
            )
            tickets.append(ticket)
        
        return tickets


# =============================================================================
# 戦略ファクトリー
# =============================================================================

class StrategyFactory:
    """戦略ファクトリー"""
    
    _strategies: dict[str, type[Strategy]] = {
        "favorite_win": FavoriteWinStrategy,
        "popularity_win": PopularityWinStrategy,
        "value_win": ValueWinStrategy,
        "favorite_place": FavoritePlaceStrategy,
        "box_quinella": BoxQuinellaStrategy,
        "flow_quinella": FlowQuinellaStrategy,
        "wheel_quinella": WheelQuinellaStrategy,
        "box_wide": BoxWideStrategy,
        "box_trio": BoxTrioStrategy,
        "flow_trio": FlowTrioStrategy,
        "formation_trio": FormationTrioStrategy,
        "hole_win": HoleHorseWinStrategy,
        "hole_place": HoleHorsePlaceStrategy,
    }
    
    @classmethod
    def create(cls, name: str, params: dict[str, Any] | None = None) -> Strategy:
        """戦略を作成
        
        Args:
            name: 戦略名
            params: 戦略パラメータ
            
        Returns:
            戦略インスタンス
            
        Raises:
            ValueError: 未知の戦略名の場合
        """
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}. Available: {list(cls._strategies.keys())}")
        
        return cls._strategies[name](params)
    
    @classmethod
    def list_strategies(cls) -> list[dict[str, str]]:
        """利用可能な戦略一覧を取得"""
        return [
            {"name": name, "description": strategy.description}
            for name, strategy in cls._strategies.items()
        ]
    
    @classmethod
    def register(cls, name: str, strategy_class: type[Strategy]) -> None:
        """カスタム戦略を登録"""
        cls._strategies[name] = strategy_class
