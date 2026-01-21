"""レースフィルター

条件に基づいてレースを絞り込む。
"""

from dataclasses import dataclass, field
from typing import Callable

from betting_simulation.models import Race, Surface


@dataclass
class FilterCondition:
    """フィルター条件"""
    tracks: list[str] = field(default_factory=list)  # 競馬場（空=全て）
    surfaces: list[Surface] = field(default_factory=list)  # 芝/ダート（空=全て）
    min_distance: int = 0  # 最小距離
    max_distance: int = 99999  # 最大距離
    years: list[int] = field(default_factory=list)  # 開催年（空=全て）
    race_numbers: list[int] = field(default_factory=list)  # レース番号（空=全て）
    min_horses: int = 0  # 最小出走頭数
    max_horses: int = 99  # 最大出走頭数
    
    @classmethod
    def from_dict(cls, data: dict) -> "FilterCondition":
        """辞書からFilterConditionを作成"""
        surfaces = []
        if "surfaces" in data:
            for s in data["surfaces"]:
                if isinstance(s, str):
                    surfaces.append(Surface.from_str(s))
                else:
                    surfaces.append(s)
        
        return cls(
            tracks=data.get("tracks", []),
            surfaces=surfaces,
            min_distance=data.get("min_distance", 0),
            max_distance=data.get("max_distance", 99999),
            years=data.get("years", []),
            race_numbers=data.get("race_numbers", []),
            min_horses=data.get("min_horses", 0),
            max_horses=data.get("max_horses", 99),
        )


class RaceFilter:
    """レースフィルター"""
    
    def __init__(self, condition: FilterCondition | None = None) -> None:
        """初期化
        
        Args:
            condition: フィルター条件。Noneの場合はフィルタリングなし
        """
        self.condition = condition or FilterCondition()
        self._custom_filters: list[Callable[[Race], bool]] = []
    
    def filter(self, races: list[Race]) -> list[Race]:
        """レースをフィルタリング
        
        Args:
            races: フィルタリング対象のレースリスト
            
        Returns:
            条件に合致するレースリスト
        """
        result = []
        for race in races:
            if self._matches(race):
                result.append(race)
        return result
    
    def _matches(self, race: Race) -> bool:
        """レースが条件に合致するか判定"""
        cond = self.condition
        
        # 競馬場
        if cond.tracks and race.track not in cond.tracks:
            return False
        
        # 芝/ダート
        if cond.surfaces and race.surface not in cond.surfaces:
            return False
        
        # 距離
        if not (cond.min_distance <= race.distance <= cond.max_distance):
            return False
        
        # 開催年
        if cond.years and race.year not in cond.years:
            return False
        
        # レース番号
        if cond.race_numbers and race.race_number not in cond.race_numbers:
            return False
        
        # 出走頭数
        if not (cond.min_horses <= race.num_horses <= cond.max_horses):
            return False
        
        # カスタムフィルター
        for custom_filter in self._custom_filters:
            if not custom_filter(race):
                return False
        
        return True
    
    def add_custom_filter(self, filter_func: Callable[[Race], bool]) -> None:
        """カスタムフィルターを追加
        
        Args:
            filter_func: Race を受け取り bool を返す関数
        """
        self._custom_filters.append(filter_func)
    
    def clear_custom_filters(self) -> None:
        """カスタムフィルターをクリア"""
        self._custom_filters.clear()


# プリセットフィルター
class PresetFilters:
    """よく使うフィルター条件のプリセット"""
    
    @staticmethod
    def turf_only() -> FilterCondition:
        """芝レースのみ"""
        return FilterCondition(surfaces=[Surface.TURF])
    
    @staticmethod
    def dirt_only() -> FilterCondition:
        """ダートレースのみ"""
        return FilterCondition(surfaces=[Surface.DIRT])
    
    @staticmethod
    def main_tracks() -> FilterCondition:
        """主要4場（東京、中山、阪神、京都）"""
        return FilterCondition(tracks=["東京", "中山", "阪神", "京都"])
    
    @staticmethod
    def sprint() -> FilterCondition:
        """スプリント（1400m以下）"""
        return FilterCondition(max_distance=1400)
    
    @staticmethod
    def mile() -> FilterCondition:
        """マイル（1400-1800m）"""
        return FilterCondition(min_distance=1400, max_distance=1800)
    
    @staticmethod
    def middle() -> FilterCondition:
        """中距離（1800-2200m）"""
        return FilterCondition(min_distance=1800, max_distance=2200)
    
    @staticmethod
    def long() -> FilterCondition:
        """長距離（2200m以上）"""
        return FilterCondition(min_distance=2200)
    
    @staticmethod
    def main_races() -> FilterCondition:
        """メインレース（10-12R）"""
        return FilterCondition(race_numbers=[10, 11, 12])
    
    @staticmethod
    def full_field() -> FilterCondition:
        """フルゲート（14頭以上）"""
        return FilterCondition(min_horses=14)
