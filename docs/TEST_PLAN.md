# テスト計画書（Test Plan Document）

## 1. 概要

本ドキュメントは、競馬賭けシミュレーションシステムのテスト計画、テスト方針、テストケース設計を定義する。

### 1.1 テスト目的

1. システムが要件定義書の機能要件を満たすことを検証
2. 各モジュールが正しく動作することを確認
3. モジュール間の連携が正常に機能することを確認
4. パフォーマンス要件を満たすことを検証
5. エッジケースやエラー処理が適切であることを確認

### 1.2 テスト範囲

| 対象 | 範囲内 | 範囲外 |
|------|-------|-------|
| ユニットテスト | 全コアモジュール | 外部ライブラリ |
| 統合テスト | モジュール間連携 | GUI操作テスト |
| パフォーマンステスト | 処理速度・メモリ | 負荷テスト |
| 回帰テスト | 修正影響範囲 | - |

---

## 2. テスト環境

### 2.1 開発・テスト環境

| 項目 | 仕様 |
|------|------|
| OS | Windows 11 / macOS / Linux |
| Python | 3.10+ |
| テストフレームワーク | pytest 7.4+ |
| カバレッジ計測 | pytest-cov |
| モック | pytest-mock, unittest.mock |
| フィクスチャ | pytest fixtures |

### 2.2 CI/CD環境

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 3. テスト方針

### 3.1 テストレベル

```
┌─────────────────────────────────────────────────────────────────┐
│                        E2Eテスト                                 │
│                    （シナリオベース）                             │
├─────────────────────────────────────────────────────────────────┤
│                       統合テスト                                 │
│               （モジュール間連携テスト）                          │
├─────────────────────────────────────────────────────────────────┤
│                      ユニットテスト                               │
│              （関数・クラス単位のテスト）                          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 テストカバレッジ目標

| レベル | 目標カバレッジ | 優先度 |
|--------|---------------|-------|
| コアモジュール | 90%以上 | 高 |
| 戦略モジュール | 85%以上 | 高 |
| 資金管理モジュール | 85%以上 | 高 |
| 出力モジュール | 70%以上 | 中 |
| ユーティリティ | 70%以上 | 中 |
| 全体 | 80%以上 | - |

### 3.3 テスト命名規則

```python
# テストファイル名
test_{module_name}.py

# テストクラス名
class Test{ClassName}:
    pass

# テストメソッド名
def test_{method_name}_{scenario}_{expected_result}(self):
    """
    テスト対象: {メソッド名}
    シナリオ: {テストシナリオの説明}
    期待結果: {期待される結果}
    """
    pass

# 例
def test_calculate_kelly_positive_expected_value_returns_positive_ratio(self):
    """
    テスト対象: calculate_kelly
    シナリオ: 期待値がプラスの場合
    期待結果: 正の賭け比率を返す
    """
    pass
```

---

## 4. ユニットテスト設計

### 4.1 DataLoader テスト

```python
# tests/unit/test_data_loader.py

import pytest
from pathlib import Path
from betting_simulation.core.data_loader import DataLoader
from betting_simulation.models import Race, Horse

class TestDataLoader:
    """DataLoaderのユニットテスト"""
    
    @pytest.fixture
    def loader(self):
        """DataLoaderインスタンス"""
        return DataLoader()
    
    @pytest.fixture
    def sample_tsv_path(self, tmp_path):
        """テスト用TSVファイル"""
        tsv_content = """競馬場\t開催年\t開催日\tレース番号\t芝ダ区分\t距離\t馬番\t馬名\t単勝オッズ\t人気順\t確定着順\t予測順位\t予測スコア
東京\t2025\t0501\t11\t芝\t1600\t1\tテスト馬1\t3.2\t1\t1\t1\t0.85
東京\t2025\t0501\t11\t芝\t1600\t2\tテスト馬2\t5.5\t2\t2\t2\t0.72
東京\t2025\t0501\t11\t芝\t1600\t3\tテスト馬3\t12.3\t5\t3\t4\t0.58"""
        
        tsv_file = tmp_path / "test_predictions.tsv"
        tsv_file.write_text(tsv_content, encoding="utf-8")
        return tsv_file
    
    # === 正常系テスト ===
    
    def test_load_valid_tsv_returns_race_list(self, loader, sample_tsv_path):
        """有効なTSVファイルを読み込むとRaceリストを返す"""
        races = loader.load(sample_tsv_path)
        
        assert isinstance(races, list)
        assert len(races) == 1
        assert isinstance(races[0], Race)
    
    def test_load_valid_tsv_race_has_correct_horses(self, loader, sample_tsv_path):
        """読み込んだRaceに正しい馬データが含まれる"""
        races = loader.load(sample_tsv_path)
        race = races[0]
        
        assert len(race.horses) == 3
        assert race.horses[0].name == "テスト馬1"
        assert race.horses[0].odds == 3.2
        assert race.horses[0].predicted_rank == 1
    
    def test_load_valid_tsv_race_has_correct_metadata(self, loader, sample_tsv_path):
        """読み込んだRaceに正しいメタデータが含まれる"""
        races = loader.load(sample_tsv_path)
        race = races[0]
        
        assert race.track == "東京"
        assert race.year == 2025
        assert race.race_number == 11
        assert race.surface == "芝"
        assert race.distance == 1600
    
    # === 異常系テスト ===
    
    def test_load_nonexistent_file_raises_error(self, loader):
        """存在しないファイルを読み込むとエラー"""
        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent.tsv")
    
    def test_load_missing_required_column_raises_error(self, loader, tmp_path):
        """必須カラムが欠けているとエラー"""
        tsv_content = """競馬場\t開催年\t馬番\t馬名
東京\t2025\t1\tテスト馬"""
        
        tsv_file = tmp_path / "invalid.tsv"
        tsv_file.write_text(tsv_content, encoding="utf-8")
        
        with pytest.raises(ValueError, match="必須カラム"):
            loader.load(tsv_file)
    
    def test_load_invalid_odds_value_logs_warning(self, loader, tmp_path, caplog):
        """不正なオッズ値は警告ログを出力"""
        tsv_content = """競馬場\t開催年\t開催日\tレース番号\t芝ダ区分\t距離\t馬番\t馬名\t単勝オッズ\t人気順\t確定着順\t予測順位\t予測スコア
東京\t2025\t0501\t11\t芝\t1600\t1\tテスト馬\tN/A\t1\t1\t1\t0.85"""
        
        tsv_file = tmp_path / "invalid_odds.tsv"
        tsv_file.write_text(tsv_content, encoding="utf-8")
        
        races = loader.load(tsv_file)
        
        assert "オッズ" in caplog.text or len(races[0].horses) == 0
    
    # === 境界値テスト ===
    
    def test_load_empty_file_returns_empty_list(self, loader, tmp_path):
        """空のファイルは空リストを返す"""
        tsv_file = tmp_path / "empty.tsv"
        tsv_file.write_text("", encoding="utf-8")
        
        races = loader.load(tsv_file)
        assert races == []
    
    def test_load_header_only_returns_empty_list(self, loader, tmp_path):
        """ヘッダーのみのファイルは空リストを返す"""
        tsv_content = "競馬場\t開催年\t開催日\tレース番号\t芝ダ区分\t距離\t馬番\t馬名\t単勝オッズ\t人気順\t確定着順\t予測順位\t予測スコア\n"
        
        tsv_file = tmp_path / "header_only.tsv"
        tsv_file.write_text(tsv_content, encoding="utf-8")
        
        races = loader.load(tsv_file)
        assert races == []
```

### 4.2 Strategy テスト

```python
# tests/unit/test_strategies.py

import pytest
from betting_simulation.strategy import (
    FavoriteWinStrategy,
    BoxQuinellaStrategy,
    ValueWinStrategy,
    StrategyFactory
)
from betting_simulation.models import Race, Horse, Ticket, TicketType

class TestFavoriteWinStrategy:
    """予測1位単勝戦略のテスト"""
    
    @pytest.fixture
    def strategy(self):
        return FavoriteWinStrategy(params={'top_n': 1})
    
    @pytest.fixture
    def sample_race(self):
        """テスト用レースデータ"""
        horses = [
            Horse(number=1, name="馬1", odds=3.2, popularity=1, 
                  actual_rank=2, predicted_rank=1, predicted_score=0.85),
            Horse(number=2, name="馬2", odds=5.5, popularity=2,
                  actual_rank=1, predicted_rank=2, predicted_score=0.72),
            Horse(number=3, name="馬3", odds=12.3, popularity=5,
                  actual_rank=3, predicted_rank=3, predicted_score=0.58),
        ]
        return Race(
            track="東京", year=2025, kaisai_date=501,
            race_number=11, surface="芝", distance=1600,
            horses=horses
        )
    
    def test_generate_tickets_returns_single_ticket(self, strategy, sample_race):
        """予測1位の単勝馬券を1枚生成"""
        tickets = strategy.generate_tickets(sample_race)
        
        assert len(tickets) == 1
        assert tickets[0].ticket_type == TicketType.WIN
        assert tickets[0].horse_numbers == (1,)  # 予測1位の馬番
    
    def test_generate_tickets_with_top_n_2(self, sample_race):
        """top_n=2の場合、2枚の馬券を生成"""
        strategy = FavoriteWinStrategy(params={'top_n': 2})
        tickets = strategy.generate_tickets(sample_race)
        
        assert len(tickets) == 2
        assert tickets[0].horse_numbers == (1,)
        assert tickets[1].horse_numbers == (2,)
    
    def test_generate_tickets_respects_min_odds(self, sample_race):
        """最小オッズを下回る馬は除外"""
        strategy = FavoriteWinStrategy(params={'top_n': 1, 'min_odds': 5.0})
        tickets = strategy.generate_tickets(sample_race)
        
        # オッズ3.2の馬は除外されるため空
        assert len(tickets) == 0
    
    def test_generate_tickets_empty_race(self, strategy):
        """出走馬がいないレースでは空リスト"""
        race = Race(track="東京", year=2025, kaisai_date=501,
                    race_number=11, surface="芝", distance=1600, horses=[])
        
        tickets = strategy.generate_tickets(race)
        assert tickets == []


class TestBoxQuinellaStrategy:
    """ボックス馬連戦略のテスト"""
    
    @pytest.fixture
    def strategy(self):
        return BoxQuinellaStrategy(params={'box_size': 4})
    
    @pytest.fixture
    def sample_race(self):
        horses = [
            Horse(number=i, name=f"馬{i}", odds=float(i*2), popularity=i,
                  actual_rank=i, predicted_rank=i, predicted_score=0.9-i*0.1)
            for i in range(1, 7)
        ]
        return Race(track="東京", year=2025, kaisai_date=501,
                    race_number=11, surface="芝", distance=1600, horses=horses)
    
    def test_generate_tickets_correct_count(self, strategy, sample_race):
        """4頭ボックスで6点（4C2=6）の馬券を生成"""
        tickets = strategy.generate_tickets(sample_race)
        assert len(tickets) == 6  # 4C2 = 6
    
    def test_generate_tickets_all_combinations(self, strategy, sample_race):
        """全ての組み合わせが含まれる"""
        tickets = strategy.generate_tickets(sample_race)
        combos = {tuple(sorted(t.horse_numbers)) for t in tickets}
        
        expected = {(1,2), (1,3), (1,4), (2,3), (2,4), (3,4)}
        assert combos == expected
    
    def test_generate_tickets_with_box_size_3(self, sample_race):
        """box_size=3の場合、3点生成"""
        strategy = BoxQuinellaStrategy(params={'box_size': 3})
        tickets = strategy.generate_tickets(sample_race)
        assert len(tickets) == 3  # 3C2 = 3


class TestValueWinStrategy:
    """期待値ベース単勝戦略のテスト"""
    
    def test_generate_tickets_filters_by_expected_value(self):
        """期待値閾値以上の馬のみ馬券生成"""
        strategy = ValueWinStrategy(params={'min_expected_value': 1.5})
        
        horses = [
            Horse(number=1, name="馬1", odds=2.0, popularity=1,
                  actual_rank=1, predicted_rank=1, predicted_score=0.8),  # EV=1.6
            Horse(number=2, name="馬2", odds=5.0, popularity=2,
                  actual_rank=2, predicted_rank=2, predicted_score=0.2),  # EV=1.0
            Horse(number=3, name="馬3", odds=10.0, popularity=3,
                  actual_rank=3, predicted_rank=3, predicted_score=0.2),  # EV=2.0
        ]
        race = Race(track="東京", year=2025, kaisai_date=501,
                    race_number=11, surface="芝", distance=1600, horses=horses)
        
        tickets = strategy.generate_tickets(race)
        
        # EV >= 1.5 の馬番1, 3のみ
        ticket_numbers = {t.horse_numbers[0] for t in tickets}
        assert ticket_numbers == {1, 3}


class TestStrategyFactory:
    """戦略ファクトリーのテスト"""
    
    def test_create_known_strategy(self):
        """既知の戦略名でインスタンス生成"""
        strategy = StrategyFactory.create("favorite_win", {})
        assert isinstance(strategy, FavoriteWinStrategy)
    
    def test_create_unknown_strategy_raises_error(self):
        """未知の戦略名でエラー"""
        with pytest.raises(ValueError, match="Unknown strategy"):
            StrategyFactory.create("unknown_strategy", {})
    
    def test_create_passes_params(self):
        """パラメータが正しく渡される"""
        strategy = StrategyFactory.create("favorite_win", {'top_n': 3})
        assert strategy.params['top_n'] == 3
```

### 4.3 FundManager テスト

```python
# tests/unit/test_fund_managers.py

import pytest
from betting_simulation.fund import (
    FixedFundManager,
    PercentageFundManager,
    KellyFundManager,
    FundManagerFactory
)
from betting_simulation.models import Ticket, TicketType

class TestFixedFundManager:
    """固定賭け金方式のテスト"""
    
    @pytest.fixture
    def manager(self):
        return FixedFundManager(
            params={'bet_amount': 1000},
            constraints={'min_bet': 100, 'max_bet_per_ticket': 5000}
        )
    
    @pytest.fixture
    def sample_ticket(self):
        return Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),
            odds=3.0,
            amount=0,
            expected_value=1.5
        )
    
    def test_calculate_bet_amount_returns_fixed_amount(self, manager, sample_ticket):
        """固定金額を返す"""
        manager.set_fund(100000)
        amount = manager.calculate_bet_amount(sample_ticket)
        assert amount == 1000
    
    def test_calculate_bet_amount_respects_max_constraint(self, sample_ticket):
        """上限制約を尊重"""
        manager = FixedFundManager(
            params={'bet_amount': 10000},
            constraints={'min_bet': 100, 'max_bet_per_ticket': 5000}
        )
        manager.set_fund(100000)
        amount = manager.calculate_bet_amount(sample_ticket)
        assert amount == 5000
    
    def test_calculate_bet_amount_below_min_returns_zero(self, sample_ticket):
        """最小賭け金未満なら0"""
        manager = FixedFundManager(
            params={'bet_amount': 50},
            constraints={'min_bet': 100}
        )
        manager.set_fund(100000)
        amount = manager.calculate_bet_amount(sample_ticket)
        assert amount == 0
    
    def test_calculate_bet_amount_insufficient_fund(self, manager, sample_ticket):
        """資金不足の場合は可能な範囲に調整"""
        manager.set_fund(500)  # 500円しかない
        amount = manager.calculate_bet_amount(sample_ticket)
        assert amount == 500


class TestPercentageFundManager:
    """資金比率方式のテスト"""
    
    @pytest.fixture
    def manager(self):
        return PercentageFundManager(
            params={'bet_percentage': 0.02},  # 2%
            constraints={'min_bet': 100}
        )
    
    @pytest.fixture
    def sample_ticket(self):
        return Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),
            odds=3.0,
            amount=0
        )
    
    def test_calculate_bet_amount_returns_percentage(self, manager, sample_ticket):
        """資金の2%を返す"""
        manager.set_fund(100000)
        amount = manager.calculate_bet_amount(sample_ticket)
        assert amount == 2000  # 100000 * 0.02 = 2000
    
    def test_calculate_bet_amount_rounds_to_100(self, manager, sample_ticket):
        """100円単位に丸める"""
        manager.set_fund(123456)
        amount = manager.calculate_bet_amount(sample_ticket)
        # 123456 * 0.02 = 2469.12 -> 2400
        assert amount % 100 == 0
    
    def test_calculate_bet_amount_scales_with_fund(self, manager, sample_ticket):
        """資金に比例して賭け金が変化"""
        manager.set_fund(50000)
        amount1 = manager.calculate_bet_amount(sample_ticket)
        
        manager.set_fund(100000)
        amount2 = manager.calculate_bet_amount(sample_ticket)
        
        assert amount2 == amount1 * 2


class TestKellyFundManager:
    """ケリー基準方式のテスト"""
    
    @pytest.fixture
    def manager(self):
        return KellyFundManager(
            params={'kelly_fraction': 0.25},  # 1/4 Kelly
            constraints={'min_bet': 100, 'max_bet_per_ticket': 10000}
        )
    
    def test_calculate_kelly_positive_ev(self, manager):
        """プラス期待値の場合、正の比率"""
        # EV = p * odds = 0.4 * 3.0 = 1.2 > 1.0
        ticket = Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),
            odds=3.0,
            amount=0,
            expected_value=1.2  # win_prob ≈ 0.4
        )
        manager.set_fund(100000)
        amount = manager.calculate_bet_amount(ticket)
        
        assert amount > 0
    
    def test_calculate_kelly_negative_ev(self, manager):
        """マイナス期待値の場合、0"""
        # EV = p * odds = 0.2 * 3.0 = 0.6 < 1.0
        ticket = Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),
            odds=3.0,
            amount=0,
            expected_value=0.6
        )
        manager.set_fund(100000)
        amount = manager.calculate_bet_amount(ticket)
        
        assert amount == 0
    
    def test_calculate_kelly_formula(self, manager):
        """ケリー基準の計算式が正しい"""
        # p=0.4, odds=3.0, b=2.0
        # kelly = (p*b - q) / b = (0.4*2 - 0.6) / 2 = 0.1
        # 1/4 kelly = 0.025
        # 100000 * 0.025 = 2500
        ticket = Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),
            odds=3.0,
            amount=0,
            expected_value=1.2
        )
        manager.set_fund(100000)
        amount = manager.calculate_bet_amount(ticket)
        
        # 許容誤差10%で検証
        assert 2200 <= amount <= 2800
    
    def test_kelly_fraction_affects_amount(self):
        """kelly_fractionが賭け金に影響"""
        ticket = Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),
            odds=3.0,
            amount=0,
            expected_value=1.5
        )
        
        manager_quarter = KellyFundManager(
            params={'kelly_fraction': 0.25},
            constraints={'min_bet': 100}
        )
        manager_half = KellyFundManager(
            params={'kelly_fraction': 0.5},
            constraints={'min_bet': 100}
        )
        
        manager_quarter.set_fund(100000)
        manager_half.set_fund(100000)
        
        amount_quarter = manager_quarter.calculate_bet_amount(ticket)
        amount_half = manager_half.calculate_bet_amount(ticket)
        
        # halfはquarterの約2倍
        assert 1.8 <= amount_half / amount_quarter <= 2.2
```

### 4.4 BetEvaluator テスト

```python
# tests/unit/test_bet_evaluator.py

import pytest
from betting_simulation.evaluator import BetEvaluator
from betting_simulation.models import Race, Horse, Ticket, TicketType

class TestBetEvaluator:
    """的中判定のテスト"""
    
    @pytest.fixture
    def evaluator(self):
        return BetEvaluator()
    
    @pytest.fixture
    def sample_race(self):
        """テスト用レース（1着:馬番2, 2着:馬番5, 3着:馬番1）"""
        horses = [
            Horse(number=1, name="馬1", odds=3.0, popularity=1, actual_rank=3,
                  predicted_rank=1, predicted_score=0.8),
            Horse(number=2, name="馬2", odds=5.0, popularity=2, actual_rank=1,
                  predicted_rank=2, predicted_score=0.7),
            Horse(number=3, name="馬3", odds=8.0, popularity=3, actual_rank=4,
                  predicted_rank=3, predicted_score=0.6),
            Horse(number=4, name="馬4", odds=12.0, popularity=4, actual_rank=5,
                  predicted_rank=4, predicted_score=0.5),
            Horse(number=5, name="馬5", odds=15.0, popularity=5, actual_rank=2,
                  predicted_rank=5, predicted_score=0.4),
        ]
        race = Race(track="東京", year=2025, kaisai_date=501,
                    race_number=11, surface="芝", distance=1600, horses=horses)
        race.payouts = {
            'win': {'horse_number': 2, 'payout': 500},
            'place': [
                {'horse_number': 2, 'payout': 180},
                {'horse_number': 5, 'payout': 320},
                {'horse_number': 1, 'payout': 150},
            ],
            'quinella': {'horse_numbers': [2, 5], 'payout': 2500},
            'wide': [
                {'horse_numbers': [2, 5], 'payout': 850},
                {'horse_numbers': [1, 2], 'payout': 380},
                {'horse_numbers': [1, 5], 'payout': 620},
            ],
            'trio': {'horse_numbers': [1, 2, 5], 'payout': 4500},
        }
        return race
    
    # === 単勝テスト ===
    
    def test_evaluate_win_hit(self, evaluator, sample_race):
        """単勝的中"""
        ticket = Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(2,),  # 1着馬
            odds=5.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is True
        assert payout == 5000  # 1000 * 5.0
    
    def test_evaluate_win_miss(self, evaluator, sample_race):
        """単勝不的中"""
        ticket = Ticket(
            ticket_type=TicketType.WIN,
            horse_numbers=(1,),  # 3着馬
            odds=3.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is False
        assert payout == 0
    
    # === 複勝テスト ===
    
    def test_evaluate_place_hit_1st(self, evaluator, sample_race):
        """複勝的中（1着馬）"""
        ticket = Ticket(
            ticket_type=TicketType.PLACE,
            horse_numbers=(2,),
            odds=1.8,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is True
        assert payout == 1800
    
    def test_evaluate_place_hit_3rd(self, evaluator, sample_race):
        """複勝的中（3着馬）"""
        ticket = Ticket(
            ticket_type=TicketType.PLACE,
            horse_numbers=(1,),
            odds=1.5,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is True
    
    def test_evaluate_place_miss(self, evaluator, sample_race):
        """複勝不的中（4着馬）"""
        ticket = Ticket(
            ticket_type=TicketType.PLACE,
            horse_numbers=(3,),  # 4着
            odds=2.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is False
        assert payout == 0
    
    # === 馬連テスト ===
    
    def test_evaluate_quinella_hit(self, evaluator, sample_race):
        """馬連的中"""
        ticket = Ticket(
            ticket_type=TicketType.QUINELLA,
            horse_numbers=(2, 5),  # 1着-2着
            odds=25.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is True
        assert payout == 25000
    
    def test_evaluate_quinella_hit_reverse_order(self, evaluator, sample_race):
        """馬連的中（逆順指定でもOK）"""
        ticket = Ticket(
            ticket_type=TicketType.QUINELLA,
            horse_numbers=(5, 2),  # 順番逆でも的中
            odds=25.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is True
    
    def test_evaluate_quinella_miss(self, evaluator, sample_race):
        """馬連不的中"""
        ticket = Ticket(
            ticket_type=TicketType.QUINELLA,
            horse_numbers=(1, 2),  # 1着-3着
            odds=10.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is False
    
    # === 三連複テスト ===
    
    def test_evaluate_trio_hit(self, evaluator, sample_race):
        """三連複的中"""
        ticket = Ticket(
            ticket_type=TicketType.TRIO,
            horse_numbers=(1, 2, 5),
            odds=45.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is True
        assert payout == 45000
    
    def test_evaluate_trio_hit_any_order(self, evaluator, sample_race):
        """三連複的中（任意の順序）"""
        ticket = Ticket(
            ticket_type=TicketType.TRIO,
            horse_numbers=(5, 1, 2),
            odds=45.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is True
    
    def test_evaluate_trio_miss(self, evaluator, sample_race):
        """三連複不的中"""
        ticket = Ticket(
            ticket_type=TicketType.TRIO,
            horse_numbers=(1, 2, 3),  # 3着じゃなくて4着の馬
            odds=30.0,
            amount=1000
        )
        is_hit, payout = evaluator.evaluate(ticket, sample_race)
        
        assert is_hit is False
```

### 4.5 MetricsCalculator テスト

```python
# tests/unit/test_metrics.py

import pytest
import numpy as np
from betting_simulation.core.metrics_calculator import MetricsCalculator

class TestMetricsCalculator:
    """評価指標計算のテスト"""
    
    @pytest.fixture
    def calculator(self):
        return MetricsCalculator()
    
    # === ROI ===
    
    def test_calculate_roi_positive(self, calculator):
        """正のROI計算"""
        roi = calculator.calculate_roi(
            total_invested=100000,
            total_payout=150000
        )
        assert roi == 150.0
    
    def test_calculate_roi_negative(self, calculator):
        """負のROI計算"""
        roi = calculator.calculate_roi(
            total_invested=100000,
            total_payout=80000
        )
        assert roi == 80.0
    
    def test_calculate_roi_zero_investment(self, calculator):
        """投資0の場合"""
        roi = calculator.calculate_roi(
            total_invested=0,
            total_payout=0
        )
        assert roi == 0.0
    
    # === 最大ドローダウン ===
    
    def test_calculate_max_drawdown_simple(self, calculator):
        """シンプルなドローダウン計算"""
        fund_history = [100, 110, 105, 120, 100, 130]
        max_dd, period = calculator.calculate_max_drawdown(fund_history)
        
        # 120 -> 100 = 16.67% のDD
        assert abs(max_dd - 16.67) < 1
    
    def test_calculate_max_drawdown_no_drawdown(self, calculator):
        """ドローダウンなし（単調増加）"""
        fund_history = [100, 110, 120, 130, 140]
        max_dd, period = calculator.calculate_max_drawdown(fund_history)
        
        assert max_dd == 0.0
    
    def test_calculate_max_drawdown_continuous_loss(self, calculator):
        """連続損失"""
        fund_history = [100, 90, 80, 70, 60]
        max_dd, period = calculator.calculate_max_drawdown(fund_history)
        
        assert max_dd == 40.0
    
    # === シャープレシオ ===
    
    def test_calculate_sharpe_ratio_positive(self, calculator):
        """正のシャープレシオ"""
        returns = [0.05, 0.03, 0.04, 0.02, 0.06]
        sharpe = calculator.calculate_sharpe_ratio(returns)
        
        assert sharpe > 0
    
    def test_calculate_sharpe_ratio_negative(self, calculator):
        """負のシャープレシオ"""
        returns = [-0.05, -0.03, -0.04, -0.02, -0.06]
        sharpe = calculator.calculate_sharpe_ratio(returns)
        
        assert sharpe < 0
    
    def test_calculate_sharpe_ratio_with_risk_free(self, calculator):
        """無リスク金利を考慮"""
        returns = [0.05, 0.03, 0.04, 0.02, 0.06]
        sharpe_no_rf = calculator.calculate_sharpe_ratio(returns, risk_free_rate=0)
        sharpe_with_rf = calculator.calculate_sharpe_ratio(returns, risk_free_rate=0.01)
        
        assert sharpe_with_rf < sharpe_no_rf
    
    # === VaR ===
    
    def test_calculate_var_95(self, calculator):
        """95% VaR計算"""
        np.random.seed(42)
        returns = np.random.normal(0.05, 0.1, 1000).tolist()
        var = calculator.calculate_var(returns, confidence=0.95)
        
        # 5%の最悪ケース
        assert var < 0  # 通常は負の値
    
    # === 的中率 ===
    
    def test_calculate_hit_rate(self, calculator):
        """的中率計算"""
        # モックのBetRecordリスト
        class MockBetRecord:
            def __init__(self, is_hit):
                self.is_hit = is_hit
        
        bet_history = [
            MockBetRecord(True),
            MockBetRecord(False),
            MockBetRecord(True),
            MockBetRecord(False),
            MockBetRecord(True),
        ]
        
        hit_rate = calculator.calculate_hit_rate(bet_history)
        assert hit_rate == 60.0
    
    # === 最大連敗 ===
    
    def test_calculate_max_consecutive_losses(self, calculator):
        """最大連敗計算"""
        class MockBetRecord:
            def __init__(self, is_hit):
                self.is_hit = is_hit
        
        # T F F F T F F T -> 最大3連敗
        bet_history = [
            MockBetRecord(True),
            MockBetRecord(False),
            MockBetRecord(False),
            MockBetRecord(False),
            MockBetRecord(True),
            MockBetRecord(False),
            MockBetRecord(False),
            MockBetRecord(True),
        ]
        
        max_losses = calculator.calculate_max_consecutive_losses(bet_history)
        assert max_losses == 3
```

---

## 5. 統合テスト設計

### 5.1 シミュレーションフロー統合テスト

```python
# tests/integration/test_simulation_flow.py

import pytest
from pathlib import Path
from betting_simulation.core import DataLoader, SimulationEngine
from betting_simulation.strategy import StrategyFactory
from betting_simulation.fund import FundManagerFactory
from betting_simulation.evaluator import BetEvaluator

class TestSimulationFlow:
    """シミュレーション全体フローのテスト"""
    
    @pytest.fixture
    def sample_data_path(self):
        return Path(__file__).parent.parent / "test_data" / "sample_predictions.tsv"
    
    @pytest.fixture
    def simulation_engine(self):
        strategy = StrategyFactory.create("favorite_win", {'top_n': 1})
        fund_manager = FundManagerFactory.create(
            "kelly",
            params={'kelly_fraction': 0.25},
            constraints={'min_bet': 100, 'max_bet_per_ticket': 5000}
        )
        evaluator = BetEvaluator()
        
        return SimulationEngine(
            strategy=strategy,
            fund_manager=fund_manager,
            evaluator=evaluator
        )
    
    def test_full_simulation_flow(self, simulation_engine, sample_data_path):
        """データ読込→シミュレーション→結果出力の全フロー"""
        # データ読込
        loader = DataLoader()
        races = loader.load(sample_data_path)
        
        assert len(races) > 0
        
        # シミュレーション実行
        result = simulation_engine.run_simple(races, initial_fund=100000)
        
        # 結果検証
        assert result is not None
        assert result.initial_fund == 100000
        assert len(result.fund_history) > 0
        assert len(result.bet_history) > 0
        assert result.metrics is not None
    
    def test_simulation_preserves_fund_consistency(self, simulation_engine, sample_data_path):
        """資金の整合性が保たれる"""
        loader = DataLoader()
        races = loader.load(sample_data_path)
        
        result = simulation_engine.run_simple(races, initial_fund=100000)
        
        # 各取引で資金が正しく推移
        for i, record in enumerate(result.bet_history):
            expected_after = record.fund_before - record.ticket.amount + record.payout
            assert abs(record.fund_after - expected_after) < 1  # 浮動小数点誤差許容
    
    def test_simulation_respects_constraints(self, sample_data_path):
        """制約が尊重される"""
        strategy = StrategyFactory.create("favorite_win", {})
        fund_manager = FundManagerFactory.create(
            "fixed",
            params={'bet_amount': 10000},
            constraints={'min_bet': 100, 'max_bet_per_ticket': 5000}
        )
        engine = SimulationEngine(
            strategy=strategy,
            fund_manager=fund_manager,
            evaluator=BetEvaluator()
        )
        
        loader = DataLoader()
        races = loader.load(sample_data_path)
        result = engine.run_simple(races, initial_fund=100000)
        
        # 全ての賭け金が制約内
        for record in result.bet_history:
            assert record.ticket.amount <= 5000
            assert record.ticket.amount >= 100 or record.ticket.amount == 0
```

### 5.2 モンテカルロ統合テスト

```python
# tests/integration/test_monte_carlo.py

import pytest
import numpy as np
from betting_simulation.core import SimulationEngine

class TestMonteCarloIntegration:
    """モンテカルロシミュレーション統合テスト"""
    
    def test_monte_carlo_reproducibility(self, simulation_engine, races):
        """同じシードで再現可能"""
        result1 = simulation_engine.run_monte_carlo(
            races, initial_fund=100000, num_trials=100, random_seed=42
        )
        result2 = simulation_engine.run_monte_carlo(
            races, initial_fund=100000, num_trials=100, random_seed=42
        )
        
        np.testing.assert_array_equal(result1.final_funds, result2.final_funds)
    
    def test_monte_carlo_different_seeds_different_results(self, simulation_engine, races):
        """異なるシードで異なる結果"""
        result1 = simulation_engine.run_monte_carlo(
            races, initial_fund=100000, num_trials=100, random_seed=42
        )
        result2 = simulation_engine.run_monte_carlo(
            races, initial_fund=100000, num_trials=100, random_seed=123
        )
        
        assert not np.array_equal(result1.final_funds, result2.final_funds)
    
    def test_monte_carlo_statistics_reasonable(self, simulation_engine, races):
        """統計値が妥当"""
        result = simulation_engine.run_monte_carlo(
            races, initial_fund=100000, num_trials=1000, random_seed=42
        )
        
        # 中央値は平均に近い（極端な歪みがない）
        mean_median_ratio = result.mean_final_fund / result.median_final_fund
        assert 0.5 < mean_median_ratio < 2.0
        
        # パーセンタイルの順序
        assert result.percentile_5 < result.percentile_25
        assert result.percentile_25 < result.median_final_fund
        assert result.median_final_fund < result.percentile_75
        assert result.percentile_75 < result.percentile_95
```

---

## 6. パフォーマンステスト

```python
# tests/performance/test_performance.py

import pytest
import time
from betting_simulation.core import DataLoader, SimulationEngine

class TestPerformance:
    """パフォーマンステスト"""
    
    @pytest.mark.slow
    def test_data_load_performance(self, large_data_path):
        """10万行のTSV読込が5秒以内"""
        loader = DataLoader()
        
        start = time.time()
        races = loader.load(large_data_path)
        elapsed = time.time() - start
        
        assert elapsed < 5.0, f"読込時間: {elapsed:.2f}秒"
    
    @pytest.mark.slow
    def test_simple_simulation_performance(self, simulation_engine, year_races):
        """1年分（約3000レース）のシミュレーションが1秒以内"""
        start = time.time()
        result = simulation_engine.run_simple(year_races, initial_fund=100000)
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"シミュレーション時間: {elapsed:.2f}秒"
    
    @pytest.mark.slow
    def test_monte_carlo_performance(self, simulation_engine, races):
        """10,000試行のモンテカルロが60秒以内"""
        start = time.time()
        result = simulation_engine.run_monte_carlo(
            races, initial_fund=100000, num_trials=10000
        )
        elapsed = time.time() - start
        
        assert elapsed < 60.0, f"モンテカルロ時間: {elapsed:.2f}秒"
    
    @pytest.mark.slow
    def test_chart_generation_performance(self, chart_generator, result):
        """全39種グラフ生成が30秒以内"""
        start = time.time()
        paths = chart_generator.generate_all(result)
        elapsed = time.time() - start
        
        assert elapsed < 30.0, f"グラフ生成時間: {elapsed:.2f}秒"
```

---

## 7. テストデータ仕様

### 7.1 テストデータファイル

| ファイル名 | 内容 | 用途 |
|-----------|------|------|
| sample_predictions.tsv | 100レース分のサンプル | 基本テスト |
| large_predictions.tsv | 10万行 | パフォーマンステスト |
| edge_case_predictions.tsv | エッジケースデータ | 境界値テスト |
| invalid_predictions.tsv | 不正データ | エラーハンドリングテスト |

### 7.2 テストデータ生成スクリプト

```python
# tests/test_data/generate_test_data.py

import random
import csv
from datetime import datetime, timedelta

def generate_sample_predictions(output_path: str, num_races: int = 100):
    """テスト用予測データを生成"""
    
    tracks = ["東京", "中山", "阪神", "京都", "中京"]
    surfaces = ["芝", "ダート"]
    distances = [1200, 1400, 1600, 1800, 2000, 2400]
    
    rows = []
    
    for race_idx in range(num_races):
        track = random.choice(tracks)
        year = 2025
        kaisai_date = 100 + race_idx % 60  # 0101 ~ 0159
        race_number = random.randint(1, 12)
        surface = random.choice(surfaces)
        distance = random.choice(distances)
        num_horses = random.randint(8, 18)
        
        # レース結果を決定
        actual_ranks = list(range(1, num_horses + 1))
        random.shuffle(actual_ranks)
        
        for horse_idx in range(num_horses):
            horse_number = horse_idx + 1
            horse_name = f"テスト馬{race_idx}_{horse_number}"
            odds = round(random.uniform(1.5, 100), 1)
            popularity = horse_idx + 1
            actual_rank = actual_ranks[horse_idx]
            predicted_rank = horse_idx + 1
            predicted_score = round(0.9 - horse_idx * 0.05, 2)
            
            rows.append({
                "競馬場": track,
                "開催年": year,
                "開催日": f"{kaisai_date:04d}",
                "レース番号": race_number,
                "芝ダ区分": surface,
                "距離": distance,
                "馬番": horse_number,
                "馬名": horse_name,
                "単勝オッズ": odds,
                "人気順": popularity,
                "確定着順": actual_rank,
                "予測順位": predicted_rank,
                "予測スコア": predicted_score,
            })
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    generate_sample_predictions("sample_predictions.tsv", 100)
```

---

## 8. 品質基準

### 8.1 合格基準

| 項目 | 基準 |
|------|------|
| ユニットテスト合格率 | 100% |
| 統合テスト合格率 | 100% |
| コードカバレッジ | 80%以上 |
| パフォーマンステスト | 全項目クリア |
| 静的解析エラー | 0件 |

### 8.2 テスト実行コマンド

```bash
# 全テスト実行
pytest

# カバレッジ付き
pytest --cov=src --cov-report=html

# ユニットテストのみ
pytest tests/unit/

# 統合テストのみ
pytest tests/integration/

# パフォーマンステスト（-m slow）
pytest -m slow

# 特定のテストファイル
pytest tests/unit/test_strategies.py

# 特定のテスト関数
pytest tests/unit/test_strategies.py::TestFavoriteWinStrategy::test_generate_tickets_returns_single_ticket

# 並列実行
pytest -n auto

# 詳細出力
pytest -v

# 失敗時に停止
pytest -x
```

---

## 9. テストスケジュール

### 9.1 開発フェーズ別テスト

| フェーズ | テスト種別 | 担当 |
|---------|----------|------|
| Phase 1（コア機能） | ユニットテスト | 開発者 |
| Phase 2（拡張機能） | ユニット + 統合 | 開発者 |
| Phase 3（可視化） | 統合テスト | 開発者 |
| Phase 4（ダッシュボード） | E2Eテスト | 開発者 |
| Phase 5（最適化） | パフォーマンステスト | 開発者 |

### 9.2 CI/CD自動テスト

- **プッシュ時**: ユニットテスト
- **PR時**: ユニット + 統合テスト + カバレッジレポート
- **マージ時**: 全テスト + パフォーマンステスト
- **リリース前**: 全テスト + 手動確認

---

**文書情報**
- 作成日: 2026-01-21
- バージョン: 1.0.0
- 関連文書: [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md), [API_INTERFACE.md](./API_INTERFACE.md)
