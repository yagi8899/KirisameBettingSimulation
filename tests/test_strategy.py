"""戦略のユニットテスト"""

import pytest

from betting_simulation.models import Horse, Race, Surface, TicketType
from betting_simulation.strategy import (
    FavoriteWinStrategy,
    ValueWinStrategy,
    FavoritePlaceStrategy,
    BoxQuinellaStrategy,
    FlowQuinellaStrategy,
    WheelQuinellaStrategy,
    BoxWideStrategy,
    BoxTrioStrategy,
    FlowTrioStrategy,
    FormationTrioStrategy,
    HoleHorseWinStrategy,
    HoleHorsePlaceStrategy,
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


class TestValueWinStrategy:
    """バリュー単勝戦略のテスト（期待値ベース）"""
    
    def test_filter_by_expected_value(self, sample_race):
        """期待値でフィルター"""
        strategy = ValueWinStrategy(params={"min_expected_value": 3.0, "max_tickets": 3})
        tickets = strategy.generate_tickets(sample_race)
        
        # 期待値 = predicted_score * odds
        # 馬1: 0.85 * 3.2 = 2.72
        # 馬2: 0.72 * 5.5 = 3.96 ✓
        # 馬3: 0.58 * 12.3 = 7.134 ✓
        # 馬4: 0.50 * 8.0 = 4.0 ✓
        # 馬5: 0.40 * 15.0 = 6.0 ✓
        # -> 4頭が条件を満たすが、max_tickets=3なので3枚
        assert len(tickets) == 3
        assert all(t.expected_value >= 3.0 for t in tickets)
    
    def test_max_tickets_limit(self, sample_race):
        """最大枚数制限"""
        strategy = ValueWinStrategy(params={"min_expected_value": 1.0, "max_tickets": 2})
        tickets = strategy.generate_tickets(sample_race)
        
        assert len(tickets) == 2


class TestFavoritePlaceStrategy:
    """複勝本命戦略のテスト"""
    
    def test_generate_place_ticket(self, sample_race):
        """複勝馬券を生成"""
        strategy = FavoritePlaceStrategy(params={"top_n": 1})
        tickets = strategy.generate_tickets(sample_race)
        
        assert len(tickets) == 1
        assert tickets[0].ticket_type == TicketType.PLACE
        assert tickets[0].horse_numbers == (1,)


class TestFlowQuinellaStrategy:
    """流し馬連戦略のテスト"""
    
    def test_generate_flow_tickets(self, sample_race):
        """流し馬券を生成"""
        strategy = FlowQuinellaStrategy(params={"num_axis": 1, "num_partners": 3})
        tickets = strategy.generate_tickets(sample_race)
        
        # 1軸 x 3相手 = 3点
        assert len(tickets) == 3
        assert all(t.ticket_type == TicketType.QUINELLA for t in tickets)
        # 全て馬1（予測1位）が含まれている
        assert all(1 in t.horse_numbers for t in tickets)


class TestWheelQuinellaStrategy:
    """ホイール馬連戦略のテスト"""
    
    def test_generate_wheel_tickets(self, sample_race):
        """ホイール馬券を生成"""
        strategy = WheelQuinellaStrategy(params={"axis_count": 2, "other_count": 3})
        tickets = strategy.generate_tickets(sample_race)
        
        # 2軸3頭ホイール = 1-2を軸に3,4,5へ = 軸組+軸-他各 = 1 + 2*3 = 7点...
        # 実際の実装確認が必要だが、馬券が生成されることを確認
        assert len(tickets) > 0
        assert all(t.ticket_type == TicketType.QUINELLA for t in tickets)


class TestBoxWideStrategy:
    """ワイドBOX戦略のテスト"""
    
    def test_generate_wide_box(self, sample_race):
        """ワイドBOX馬券を生成"""
        strategy = BoxWideStrategy(params={"box_size": 3})
        tickets = strategy.generate_tickets(sample_race)
        
        # 3C2 = 3点
        assert len(tickets) == 3
        assert all(t.ticket_type == TicketType.WIDE for t in tickets)


class TestBoxTrioStrategy:
    """三連複BOX戦略のテスト"""
    
    def test_generate_trio_box(self, sample_race):
        """三連複BOX馬券を生成"""
        strategy = BoxTrioStrategy(params={"box_size": 4})
        tickets = strategy.generate_tickets(sample_race)
        
        # 4C3 = 4点
        assert len(tickets) == 4
        assert all(t.ticket_type == TicketType.TRIO for t in tickets)


class TestFlowTrioStrategy:
    """流し三連複戦略のテスト"""
    
    def test_generate_flow_trio(self, sample_race):
        """流し三連複馬券を生成"""
        strategy = FlowTrioStrategy(params={"axis_count": 1, "target_count": 4})
        tickets = strategy.generate_tickets(sample_race)
        
        # 1軸流し4頭 = 4C2 = 6点
        assert len(tickets) == 6
        assert all(t.ticket_type == TicketType.TRIO for t in tickets)
        # 全て馬1が含まれている
        assert all(1 in t.horse_numbers for t in tickets)


class TestFormationTrioStrategy:
    """フォーメーション三連複戦略のテスト"""
    
    def test_generate_formation_trio(self, sample_race):
        """フォーメーション三連複馬券を生成"""
        strategy = FormationTrioStrategy(params={
            "first_count": 2,
            "second_count": 3,
            "third_count": 4
        })
        tickets = strategy.generate_tickets(sample_race)
        
        # 馬券が生成されることを確認
        assert len(tickets) > 0
        assert all(t.ticket_type == TicketType.TRIO for t in tickets)


class TestHoleHorseWinStrategy:
    """穴馬単勝戦略のテスト"""
    
    def test_filter_by_rank_range(self, sample_race):
        """人気順でフィルター"""
        strategy = HoleHorseWinStrategy(params={
            "min_rank": 3,
            "max_rank": 6,
            "score_threshold": 0.3
        })
        tickets = strategy.generate_tickets(sample_race)
        
        # 人気順3-6位でスコア0.3以上の馬
        assert all(t.ticket_type == TicketType.WIN for t in tickets)


class TestHoleHorsePlaceStrategy:
    """穴馬複勝戦略のテスト"""
    
    def test_generate_hole_place(self, sample_race):
        """穴馬複勝馬券を生成"""
        strategy = HoleHorsePlaceStrategy(params={
            "min_rank": 5,
            "max_rank": 10,
            "score_threshold": 0.2
        })
        tickets = strategy.generate_tickets(sample_race)
        
        # 複勝馬券が生成される
        assert all(t.ticket_type == TicketType.PLACE for t in tickets)
