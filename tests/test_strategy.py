"""戦略のユニットテスト"""

import pytest

from betting_simulation.models import Horse, Race, Surface, TicketType
from betting_simulation.strategy import (
    FavoriteWinStrategy,
    BoxQuinellaStrategy,
    StrategyFactory,
)


@pytest.fixture
def sample_race():
    """テスト用レースデータ"""
    horses = [
        Horse(number=1, name="馬1", odds=3.2, popularity=1, 
              actual_rank=2, predicted_rank=1, predicted_score=0.85),
        Horse(number=2, name="馬2", odds=5.5, popularity=2,
              actual_rank=1, predicted_rank=2, predicted_score=0.72),
        Horse(number=3, name="馬3", odds=12.3, popularity=5,
              actual_rank=3, predicted_rank=3, predicted_score=0.58),
        Horse(number=4, name="馬4", odds=8.0, popularity=3,
              actual_rank=4, predicted_rank=4, predicted_score=0.50),
        Horse(number=5, name="馬5", odds=15.0, popularity=6,
              actual_rank=5, predicted_rank=5, predicted_score=0.40),
    ]
    return Race(
        track="東京", year=2025, kaisai_date=501,
        race_number=11, surface=Surface.TURF, distance=1600,
        horses=horses
    )


class TestFavoriteWinStrategy:
    """予測1位単勝戦略のテスト"""
    
    def test_generate_single_ticket(self, sample_race):
        """1枚の馬券を生成"""
        strategy = FavoriteWinStrategy(params={"top_n": 1})
        tickets = strategy.generate_tickets(sample_race)
        
        assert len(tickets) == 1
        assert tickets[0].ticket_type == TicketType.WIN
        assert tickets[0].horse_numbers == (1,)
    
    def test_generate_multiple_tickets(self, sample_race):
        """複数枚の馬券を生成"""
        strategy = FavoriteWinStrategy(params={"top_n": 3})
        tickets = strategy.generate_tickets(sample_race)
        
        assert len(tickets) == 3
        assert tickets[0].horse_numbers == (1,)
        assert tickets[1].horse_numbers == (2,)
        assert tickets[2].horse_numbers == (3,)
    
    def test_min_odds_filter(self, sample_race):
        """最小オッズフィルター"""
        strategy = FavoriteWinStrategy(params={"top_n": 3, "min_odds": 5.0})
        tickets = strategy.generate_tickets(sample_race)
        
        # オッズ3.2の馬1は除外される
        assert len(tickets) == 2
        assert all(t.odds >= 5.0 for t in tickets)


class TestBoxQuinellaStrategy:
    """ボックス馬連戦略のテスト"""
    
    def test_generate_correct_count(self, sample_race):
        """正しい点数を生成"""
        strategy = BoxQuinellaStrategy(params={"box_size": 4})
        tickets = strategy.generate_tickets(sample_race)
        
        # 4C2 = 6点
        assert len(tickets) == 6
    
    def test_all_tickets_are_quinella(self, sample_race):
        """全て馬連馬券"""
        strategy = BoxQuinellaStrategy(params={"box_size": 3})
        tickets = strategy.generate_tickets(sample_race)
        
        assert all(t.ticket_type == TicketType.QUINELLA for t in tickets)
    
    def test_all_combinations_covered(self, sample_race):
        """全組み合わせがカバーされる"""
        strategy = BoxQuinellaStrategy(params={"box_size": 3})
        tickets = strategy.generate_tickets(sample_race)
        
        combos = {tuple(sorted(t.horse_numbers)) for t in tickets}
        expected = {(1, 2), (1, 3), (2, 3)}
        assert combos == expected


class TestStrategyFactory:
    """戦略ファクトリーのテスト"""
    
    def test_create_favorite_win(self):
        """favorite_win戦略を作成"""
        strategy = StrategyFactory.create("favorite_win", {"top_n": 2})
        assert isinstance(strategy, FavoriteWinStrategy)
        assert strategy.params["top_n"] == 2
    
    def test_create_unknown_raises_error(self):
        """未知の戦略名でエラー"""
        with pytest.raises(ValueError, match="Unknown strategy"):
            StrategyFactory.create("unknown_strategy", {})
    
    def test_list_strategies(self):
        """戦略一覧を取得"""
        strategies = StrategyFactory.list_strategies()
        assert len(strategies) > 0
        assert all("name" in s for s in strategies)
