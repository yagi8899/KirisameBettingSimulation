# 戦略・アルゴリズム設計書（Strategy & Algorithm Design Document）

## 1. 概要

本ドキュメントは、競馬賭けシミュレーションシステムにおける賭け戦略、資金管理方式、シミュレーションアルゴリズムの詳細設計を定義する。

---

## 2. 賭け戦略エンジン

### 2.1 戦略基底クラス設計

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from models import Race, Ticket

class BaseStrategy(ABC):
    """賭け戦略の抽象基底クラス"""
    
    def __init__(self, params: Dict[str, Any]):
        """
        Args:
            params: 戦略固有のパラメータ
        """
        self.params = params
        self._validate_params()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """戦略名"""
        pass
    
    @property
    @abstractmethod
    def ticket_type(self) -> str:
        """対象馬券種別"""
        pass
    
    @abstractmethod
    def _validate_params(self) -> None:
        """パラメータバリデーション"""
        pass
    
    @abstractmethod
    def generate_tickets(self, race: Race) -> List[Ticket]:
        """
        レースに対して購入馬券を生成
        
        Args:
            race: レースデータ
            
        Returns:
            購入馬券のリスト
        """
        pass
    
    def should_bet(self, race: Race) -> bool:
        """
        このレースで賭けるべきかを判定
        
        Args:
            race: レースデータ
            
        Returns:
            賭けるべきならTrue
        """
        return True  # デフォルトは常にTrue、サブクラスでオーバーライド可
```

---

### 2.2 単勝戦略

#### 2.2.1 favorite_win（予測1位単勝）

**概要**: 予測順位1位の馬の単勝を購入する最もシンプルな戦略。

```python
class FavoriteWinStrategy(BaseStrategy):
    """予測1位の単勝を購入"""
    
    name = "favorite_win"
    ticket_type = "win"
    
    # パラメータ
    # - top_n: int = 1  予測上位何頭を対象にするか
    # - min_odds: float = 1.1  最小オッズ（これ以下は見送り）
    # - max_odds: float = 100.0  最大オッズ
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        tickets = []
        top_horses = race.get_horses_by_predicted_rank(self.params.get('top_n', 1))
        
        for horse in top_horses:
            if self._is_valid_odds(horse.odds):
                ticket = Ticket(
                    ticket_type=TicketType.WIN,
                    horse_numbers=(horse.number,),
                    odds=horse.odds,
                    amount=0,  # FundManagerで設定
                    strategy_name=self.name,
                    expected_value=horse.expected_value
                )
                tickets.append(ticket)
        
        return tickets
```

**アルゴリズム**:
1. 予測順位でソートし、上位N頭を取得
2. オッズフィルタ（min_odds ≤ odds ≤ max_odds）
3. 条件を満たす馬の単勝馬券を生成

#### 2.2.2 longshot_win（穴馬単勝）

**概要**: 穴馬候補の単勝を購入。高配当を狙う戦略。

```python
class LongshotWinStrategy(BaseStrategy):
    """穴馬候補の単勝を購入"""
    
    name = "longshot_win"
    ticket_type = "win"
    
    # パラメータ
    # - upset_threshold: float = 0.5  穴馬確率の閾値
    # - max_candidates: int = 2  最大購入頭数
    # - min_odds: float = 10.0  最小オッズ
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        tickets = []
        candidates = [
            h for h in race.horses 
            if h.upset_prob >= self.params.get('upset_threshold', 0.5)
        ]
        # 穴馬確率の高い順にソート
        candidates.sort(key=lambda h: h.upset_prob, reverse=True)
        
        for horse in candidates[:self.params.get('max_candidates', 2)]:
            if horse.odds >= self.params.get('min_odds', 10.0):
                ticket = Ticket(
                    ticket_type=TicketType.WIN,
                    horse_numbers=(horse.number,),
                    odds=horse.odds,
                    amount=0,
                    strategy_name=self.name,
                    expected_value=horse.upset_prob * horse.odds
                )
                tickets.append(ticket)
        
        return tickets
```

**アルゴリズム**:
1. 穴馬確率が閾値以上の馬を抽出
2. 穴馬確率の高い順にソート
3. 上位N頭（max_candidates）の単勝を購入

#### 2.2.3 value_win（バリュー単勝）

**概要**: 期待値が閾値以上の馬の単勝を購入。

```python
class ValueWinStrategy(BaseStrategy):
    """期待値ベースの単勝購入"""
    
    name = "value_win"
    ticket_type = "win"
    
    # パラメータ
    # - min_expected_value: float = 1.2  最小期待値
    # - max_tickets: int = 3  最大購入点数
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        tickets = []
        min_ev = self.params.get('min_expected_value', 1.2)
        
        # 期待値計算: EV = 予測スコア × オッズ
        value_horses = [
            h for h in race.horses
            if h.expected_value >= min_ev
        ]
        value_horses.sort(key=lambda h: h.expected_value, reverse=True)
        
        for horse in value_horses[:self.params.get('max_tickets', 3)]:
            ticket = Ticket(
                ticket_type=TicketType.WIN,
                horse_numbers=(horse.number,),
                odds=horse.odds,
                amount=0,
                strategy_name=self.name,
                expected_value=horse.expected_value
            )
            tickets.append(ticket)
        
        return tickets
```

**期待値計算式**:
$$EV = P_{win} \times Odds$$

ここで、$P_{win}$ は予測スコア（勝利確率の推定値）、$Odds$ は単勝オッズ。

---

### 2.3 複勝戦略

#### 2.3.1 favorite_place（予測上位複勝）

**概要**: 予測上位の複勝を購入。的中率重視の安定志向戦略。

```python
class FavoritePlaceStrategy(BaseStrategy):
    """予測上位の複勝を購入"""
    
    name = "favorite_place"
    ticket_type = "place"
    
    # パラメータ
    # - top_n: int = 2  予測上位何頭を対象にするか
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        tickets = []
        top_horses = race.get_horses_by_predicted_rank(self.params.get('top_n', 2))
        
        for horse in top_horses:
            if horse.place_odds_min:
                # 複勝オッズは下限を使用
                odds = horse.place_odds_min
            else:
                # 複勝オッズがない場合は単勝オッズから推定
                odds = self._estimate_place_odds(horse.odds)
            
            ticket = Ticket(
                ticket_type=TicketType.PLACE,
                horse_numbers=(horse.number,),
                odds=odds,
                amount=0,
                strategy_name=self.name
            )
            tickets.append(ticket)
        
        return tickets
    
    def _estimate_place_odds(self, win_odds: float) -> float:
        """単勝オッズから複勝オッズを推定"""
        # 経験則: 複勝オッズ ≈ 単勝オッズ × 0.3〜0.4
        return max(1.1, win_odds * 0.35)
```

#### 2.3.2 longshot_place（穴馬複勝）

**概要**: 穴馬候補の複勝を購入。単勝よりリスクを抑えつつ高配当を狙う。

---

### 2.4 馬連戦略

#### 2.4.1 favorite_quinella（本命馬連）

**概要**: 予測上位2頭の馬連を購入。

```python
class FavoriteQuinellaStrategy(BaseStrategy):
    """予測上位2頭の馬連"""
    
    name = "favorite_quinella"
    ticket_type = "quinella"
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        top_horses = race.get_horses_by_predicted_rank(2)
        
        if len(top_horses) < 2:
            return []
        
        h1, h2 = top_horses[0], top_horses[1]
        odds = self._get_quinella_odds(race, h1.number, h2.number)
        
        if odds is None:
            return []
        
        return [Ticket(
            ticket_type=TicketType.QUINELLA,
            horse_numbers=tuple(sorted([h1.number, h2.number])),
            odds=odds,
            amount=0,
            strategy_name=self.name
        )]
```

#### 2.4.2 favorite_longshot_quinella（本命-穴馬馬連）

**概要**: 予測1位を軸に、穴馬候補への流し馬連。

```python
class FavoriteLongshotQuinellaStrategy(BaseStrategy):
    """本命軸-穴馬相手の馬連"""
    
    name = "favorite_longshot_quinella"
    ticket_type = "quinella"
    
    # パラメータ
    # - upset_threshold: float = 0.5
    # - max_counterparts: int = 3  相手馬の最大数
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        tickets = []
        
        # 軸馬（予測1位）
        favorite = race.get_horses_by_predicted_rank(1)[0]
        
        # 穴馬候補
        upset_candidates = [
            h for h in race.horses
            if h.upset_prob >= self.params.get('upset_threshold', 0.5)
            and h.number != favorite.number
        ]
        upset_candidates.sort(key=lambda h: h.upset_prob, reverse=True)
        
        for counterpart in upset_candidates[:self.params.get('max_counterparts', 3)]:
            odds = self._get_quinella_odds(race, favorite.number, counterpart.number)
            if odds:
                tickets.append(Ticket(
                    ticket_type=TicketType.QUINELLA,
                    horse_numbers=tuple(sorted([favorite.number, counterpart.number])),
                    odds=odds,
                    amount=0,
                    strategy_name=self.name
                ))
        
        return tickets
```

#### 2.4.3 box_quinella（ボックス馬連）

**概要**: 予測上位N頭のボックス（全組み合わせ）で購入。

```python
class BoxQuinellaStrategy(BaseStrategy):
    """予測上位N頭のボックス馬連"""
    
    name = "box_quinella"
    ticket_type = "quinella"
    
    # パラメータ
    # - box_size: int = 4  ボックスに含める頭数
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        tickets = []
        box_size = self.params.get('box_size', 4)
        top_horses = race.get_horses_by_predicted_rank(box_size)
        
        # 全組み合わせを生成
        from itertools import combinations
        for h1, h2 in combinations(top_horses, 2):
            odds = self._get_quinella_odds(race, h1.number, h2.number)
            if odds:
                tickets.append(Ticket(
                    ticket_type=TicketType.QUINELLA,
                    horse_numbers=tuple(sorted([h1.number, h2.number])),
                    odds=odds,
                    amount=0,
                    strategy_name=self.name
                ))
        
        return tickets
```

**点数計算**:
$$\text{点数} = \binom{n}{2} = \frac{n(n-1)}{2}$$

| ボックスサイズ | 点数 |
|---------------|------|
| 3頭 | 3点 |
| 4頭 | 6点 |
| 5頭 | 10点 |
| 6頭 | 15点 |

---

### 2.5 ワイド戦略

#### 2.5.1 favorite_wide（本命ワイド）

予測上位2頭のワイド購入。馬連より的中範囲が広い。

#### 2.5.2 favorite_longshot_wide（保険ワイド）

本命-穴馬のワイド。馬連の保険として併用。

#### 2.5.3 box_wide（ボックスワイド）

予測上位N頭のワイドボックス。

---

### 2.6 三連複戦略

#### 2.6.1 favorite_trio（本命三連複）

```python
class FavoriteTrioStrategy(BaseStrategy):
    """予測上位3頭の三連複"""
    
    name = "favorite_trio"
    ticket_type = "trio"
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        top_horses = race.get_horses_by_predicted_rank(3)
        
        if len(top_horses) < 3:
            return []
        
        numbers = tuple(sorted([h.number for h in top_horses]))
        odds = self._get_trio_odds(race, numbers)
        
        if odds is None:
            return []
        
        return [Ticket(
            ticket_type=TicketType.TRIO,
            horse_numbers=numbers,
            odds=odds,
            amount=0,
            strategy_name=self.name
        )]
```

#### 2.6.2 favorite2_longshot_trio（2頭軸穴馬流し）

```python
class Favorite2LongshotTrioStrategy(BaseStrategy):
    """本命2頭軸-穴馬流しの三連複"""
    
    name = "favorite2_longshot_trio"
    ticket_type = "trio"
    
    # パラメータ
    # - upset_threshold: float = 0.5
    # - max_counterparts: int = 3
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        tickets = []
        
        # 軸馬2頭（予測1位、2位）
        axis_horses = race.get_horses_by_predicted_rank(2)
        if len(axis_horses) < 2:
            return []
        
        axis_numbers = [h.number for h in axis_horses]
        
        # 穴馬候補
        upset_candidates = [
            h for h in race.horses
            if h.upset_prob >= self.params.get('upset_threshold', 0.5)
            and h.number not in axis_numbers
        ]
        upset_candidates.sort(key=lambda h: h.upset_prob, reverse=True)
        
        for counterpart in upset_candidates[:self.params.get('max_counterparts', 3)]:
            numbers = tuple(sorted(axis_numbers + [counterpart.number]))
            odds = self._get_trio_odds(race, numbers)
            if odds:
                tickets.append(Ticket(
                    ticket_type=TicketType.TRIO,
                    horse_numbers=numbers,
                    odds=odds,
                    amount=0,
                    strategy_name=self.name
                ))
        
        return tickets
```

#### 2.6.3 formation_trio（フォーメーション）

```python
class FormationTrioStrategy(BaseStrategy):
    """フォーメーション三連複"""
    
    name = "formation_trio"
    ticket_type = "trio"
    
    # パラメータ
    # - first_leg: List[int] = [1, 2]  1列目の予測順位
    # - second_leg: List[int] = [1, 2, 3]  2列目の予測順位
    # - third_leg: List[int] = [1, 2, 3, 4, 5]  3列目の予測順位
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        tickets = []
        
        first_leg = self.params.get('first_leg', [1, 2])
        second_leg = self.params.get('second_leg', [1, 2, 3])
        third_leg = self.params.get('third_leg', [1, 2, 3, 4, 5])
        
        # 各列の馬番を取得
        first_numbers = [race.get_horses_by_predicted_rank(r)[0].number for r in first_leg if r <= len(race.horses)]
        second_numbers = [race.get_horses_by_predicted_rank(r)[0].number for r in second_leg if r <= len(race.horses)]
        third_numbers = [race.get_horses_by_predicted_rank(r)[0].number for r in third_leg if r <= len(race.horses)]
        
        # フォーメーション組み合わせを生成
        seen = set()
        for n1 in first_numbers:
            for n2 in second_numbers:
                for n3 in third_numbers:
                    if len({n1, n2, n3}) == 3:  # 3頭が異なる
                        combo = tuple(sorted([n1, n2, n3]))
                        if combo not in seen:
                            seen.add(combo)
                            odds = self._get_trio_odds(race, combo)
                            if odds:
                                tickets.append(Ticket(
                                    ticket_type=TicketType.TRIO,
                                    horse_numbers=combo,
                                    odds=odds,
                                    amount=0,
                                    strategy_name=self.name
                                ))
        
        return tickets
```

---

### 2.7 複合戦略

```python
class CompositeStrategy(BaseStrategy):
    """複数戦略の組み合わせ"""
    
    name = "composite"
    ticket_type = "mixed"
    
    def __init__(self, strategies: List[Tuple[BaseStrategy, float]]):
        """
        Args:
            strategies: [(戦略, 重み), ...] のリスト
        """
        self.strategies = strategies
        total_weight = sum(w for _, w in strategies)
        self.normalized_weights = [(s, w / total_weight) for s, w in strategies]
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        all_tickets = []
        
        for strategy, weight in self.normalized_weights:
            tickets = strategy.generate_tickets(race)
            for ticket in tickets:
                # 重みを属性として保持（FundManagerで使用）
                ticket.weight = weight
                all_tickets.append(ticket)
        
        return all_tickets
```

---

## 3. 資金管理エンジン

### 3.1 資金管理基底クラス

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseFundManager(ABC):
    """資金管理の抽象基底クラス"""
    
    def __init__(self, params: Dict[str, Any], constraints: Dict[str, Any]):
        self.params = params
        self.constraints = constraints
        self.current_fund = 0.0
    
    def set_fund(self, fund: float) -> None:
        """現在資金を設定"""
        self.current_fund = fund
    
    @abstractmethod
    def calculate_bet_amount(self, ticket: Ticket) -> int:
        """
        賭け金を計算
        
        Args:
            ticket: 馬券データ
            
        Returns:
            賭け金（円）、100円単位に丸め
        """
        pass
    
    def apply_constraints(self, amount: int, ticket: Ticket) -> int:
        """制約を適用"""
        # 最小賭け金チェック
        if amount < self.constraints.get('min_bet', 100):
            return 0  # 見送り
        
        # 1点上限チェック
        max_per_ticket = self.constraints.get('max_bet_per_ticket', float('inf'))
        amount = min(amount, max_per_ticket)
        
        # 残資金チェック
        if amount > self.current_fund:
            amount = int(self.current_fund // 100) * 100
        
        # 100円単位に丸め
        return int(amount // 100) * 100
```

### 3.2 固定賭け金方式（Fixed）

```python
class FixedFundManager(BaseFundManager):
    """固定賭け金方式"""
    
    def calculate_bet_amount(self, ticket: Ticket) -> int:
        """
        1点あたり固定金額を返す
        
        パラメータ:
            bet_amount: int  1点あたりの賭け金（デフォルト: 1000円）
        """
        base_amount = self.params.get('bet_amount', 1000)
        return self.apply_constraints(base_amount, ticket)
```

**特徴**:
- シンプルで理解しやすい
- 資金の増減に関わらず同じ金額
- 資金が少ない時は相対的にリスク大

### 3.3 資金比率方式（Percentage）

```python
class PercentageFundManager(BaseFundManager):
    """資金比率方式"""
    
    def calculate_bet_amount(self, ticket: Ticket) -> int:
        """
        現在資金の一定比率を賭け金とする
        
        パラメータ:
            bet_percentage: float  資金に対する比率（デフォルト: 0.02 = 2%）
        """
        percentage = self.params.get('bet_percentage', 0.02)
        base_amount = self.current_fund * percentage
        return self.apply_constraints(int(base_amount), ticket)
```

**計算式**:
$$\text{賭け金} = \text{現在資金} \times \text{比率}$$

**特徴**:
- 資金が増えれば賭け金も増加
- 資金が減れば賭け金も減少（自動的にリスク調整）
- 複利効果を期待できる

### 3.4 ケリー基準方式（Kelly Criterion）

```python
class KellyFundManager(BaseFundManager):
    """ケリー基準方式"""
    
    def calculate_bet_amount(self, ticket: Ticket) -> int:
        """
        ケリー基準に基づき最適賭け金を計算
        
        パラメータ:
            kelly_fraction: float  ケリー比率（デフォルト: 0.25 = 1/4 Kelly）
        """
        # 勝率推定（期待値から逆算）
        if ticket.odds <= 1:
            return 0
        
        win_prob = ticket.expected_value / ticket.odds if ticket.odds > 0 else 0
        win_prob = min(max(win_prob, 0.01), 0.99)  # 1%-99%にクリップ
        
        # ケリー基準計算
        kelly_ratio = self._calculate_kelly(win_prob, ticket.odds)
        
        # フラクションを適用
        fraction = self.params.get('kelly_fraction', 0.25)
        adjusted_ratio = kelly_ratio * fraction
        
        # 賭け金計算
        base_amount = self.current_fund * adjusted_ratio
        return self.apply_constraints(int(base_amount), ticket)
    
    def _calculate_kelly(self, win_prob: float, odds: float) -> float:
        """
        ケリー基準を計算
        
        f* = (p * b - q) / b
        
        ここで:
            p: 勝率
            q: 敗率 (1 - p)
            b: 純オッズ (odds - 1)
        """
        p = win_prob
        q = 1 - p
        b = odds - 1  # 純オッズ（配当から元本を引いた倍率）
        
        if b <= 0:
            return 0.0
        
        kelly = (p * b - q) / b
        
        # 負の値はベットしない
        return max(0.0, kelly)
```

**ケリー基準の数式**:
$$f^* = \frac{pb - q}{b}$$

ここで:
- $f^*$: 最適賭け比率
- $p$: 勝率
- $q$: 敗率（$1-p$）
- $b$: 純オッズ（オッズ $- 1$）

**フラクショナルケリー**:

フルケリーはボラティリティが高いため、通常は1/4〜1/2ケリーを使用：
$$f_{adjusted} = f^* \times \text{fraction}$$

| フラクション | 特徴 |
|-------------|------|
| 1.0（フルケリー） | 最大成長率、高ボラティリティ |
| 0.5（ハーフケリー） | バランス型 |
| 0.25（クォーターケリー） | 保守的、低ボラティリティ |

---

## 4. シミュレーションエンジン

### 4.1 単純シミュレーション

```python
class SimpleSimulation:
    """過去データを時系列順に処理するシミュレーション"""
    
    def run(
        self,
        races: List[Race],
        strategy: BaseStrategy,
        fund_manager: BaseFundManager,
        initial_fund: float
    ) -> SimulationResult:
        
        fund_history = [initial_fund]
        bet_history = []
        current_fund = initial_fund
        
        # レースを日付順にソート
        sorted_races = sorted(races, key=lambda r: (r.year, r.kaisai_date, r.race_number))
        
        for race in sorted_races:
            # 戦略で馬券生成
            tickets = strategy.generate_tickets(race)
            
            for ticket in tickets:
                # 資金管理で賭け金計算
                fund_manager.set_fund(current_fund)
                amount = fund_manager.calculate_bet_amount(ticket)
                
                if amount == 0:
                    continue  # 見送り
                
                ticket.amount = amount
                
                # 購入前資金
                fund_before = current_fund
                current_fund -= amount
                
                # 的中判定
                is_hit, payout = self.evaluator.evaluate(ticket, race)
                current_fund += payout
                
                # 記録
                bet_history.append(BetRecord(
                    race_id=race.race_id,
                    race_date=race.race_date,
                    ticket=ticket,
                    is_hit=is_hit,
                    payout=payout,
                    fund_before=fund_before,
                    fund_after=current_fund
                ))
                
                fund_history.append(current_fund)
                
                # 破産チェック
                if current_fund < fund_manager.constraints.get('min_bet', 100):
                    break
        
        # 評価指標計算
        metrics = self.metrics_calculator.calculate(fund_history, bet_history, initial_fund)
        
        return SimulationResult(
            simulation_type="simple",
            initial_fund=initial_fund,
            final_fund=current_fund,
            fund_history=fund_history,
            bet_history=bet_history,
            metrics=metrics
        )
```

### 4.2 モンテカルロシミュレーション

```python
import numpy as np
from typing import Callable

class MonteCarloSimulation:
    """モンテカルロシミュレーション"""
    
    def __init__(self, num_trials: int = 10000, random_seed: int = 42):
        self.num_trials = num_trials
        self.random_seed = random_seed
    
    def run(
        self,
        races: List[Race],
        strategy: BaseStrategy,
        fund_manager: BaseFundManager,
        initial_fund: float,
        method: str = "bootstrap"
    ) -> MonteCarloResult:
        
        np.random.seed(self.random_seed)
        
        if method == "bootstrap":
            return self._bootstrap_simulation(races, strategy, fund_manager, initial_fund)
        elif method == "probability_based":
            return self._probability_simulation(races, strategy, fund_manager, initial_fund)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _bootstrap_simulation(
        self,
        races: List[Race],
        strategy: BaseStrategy,
        fund_manager: BaseFundManager,
        initial_fund: float
    ) -> MonteCarloResult:
        """
        ブートストラップ法によるモンテカルロシミュレーション
        
        過去のレースデータをランダムにリサンプリングして
        多数のシナリオを生成する
        """
        final_funds = []
        all_histories = []
        
        num_races = len(races)
        
        for trial in range(self.num_trials):
            # ブートストラップサンプリング
            sampled_indices = np.random.choice(num_races, size=num_races, replace=True)
            sampled_races = [races[i] for i in sampled_indices]
            
            # シミュレーション実行
            result = SimpleSimulation().run(
                sampled_races, strategy, fund_manager, initial_fund
            )
            
            final_funds.append(result.final_fund)
            all_histories.append(result.fund_history)
        
        return self._create_mc_result(final_funds, all_histories, initial_fund)
    
    def _probability_simulation(
        self,
        races: List[Race],
        strategy: BaseStrategy,
        fund_manager: BaseFundManager,
        initial_fund: float
    ) -> MonteCarloResult:
        """
        確率分布ベースのモンテカルロシミュレーション
        
        各馬券の的中確率に基づいてランダムに結果を生成
        """
        final_funds = []
        all_histories = []
        
        for trial in range(self.num_trials):
            fund_history = [initial_fund]
            current_fund = initial_fund
            
            for race in races:
                tickets = strategy.generate_tickets(race)
                
                for ticket in tickets:
                    fund_manager.set_fund(current_fund)
                    amount = fund_manager.calculate_bet_amount(ticket)
                    
                    if amount == 0:
                        continue
                    
                    ticket.amount = amount
                    current_fund -= amount
                    
                    # 確率的に的中判定
                    hit_prob = self._estimate_hit_probability(ticket, race)
                    is_hit = np.random.random() < hit_prob
                    
                    if is_hit:
                        payout = int(amount * ticket.odds)
                        current_fund += payout
                    
                    fund_history.append(current_fund)
                    
                    if current_fund < 100:
                        break
                
                if current_fund < 100:
                    break
            
            final_funds.append(current_fund)
            all_histories.append(fund_history)
        
        return self._create_mc_result(final_funds, all_histories, initial_fund)
    
    def _estimate_hit_probability(self, ticket: Ticket, race: Race) -> float:
        """馬券の的中確率を推定"""
        # 馬券種別ごとの確率推定
        # 実際の予測スコアや穴馬確率から計算
        pass
    
    def _create_mc_result(
        self,
        final_funds: List[float],
        all_histories: List[List[float]],
        initial_fund: float
    ) -> MonteCarloResult:
        """モンテカルロ結果オブジェクトを生成"""
        final_funds_arr = np.array(final_funds)
        
        return MonteCarloResult(
            num_trials=self.num_trials,
            random_seed=self.random_seed,
            final_funds=final_funds_arr,
            mean_final_fund=np.mean(final_funds_arr),
            median_final_fund=np.median(final_funds_arr),
            std_final_fund=np.std(final_funds_arr),
            percentile_5=np.percentile(final_funds_arr, 5),
            percentile_25=np.percentile(final_funds_arr, 25),
            percentile_75=np.percentile(final_funds_arr, 75),
            percentile_95=np.percentile(final_funds_arr, 95),
            bankruptcy_probability=np.mean(final_funds_arr < initial_fund * 0.1) * 100,
            all_fund_histories=all_histories
        )
```

### 4.3 Walk-Forwardシミュレーション

```python
from datetime import datetime, timedelta

class WalkForwardSimulation:
    """Walk-Forwardシミュレーション"""
    
    def __init__(
        self,
        train_period_days: int = 180,
        test_period_days: int = 30,
        step_days: int = 30
    ):
        self.train_period = train_period_days
        self.test_period = test_period_days
        self.step = step_days
    
    def run(
        self,
        races: List[Race],
        strategy: BaseStrategy,
        fund_manager: BaseFundManager,
        initial_fund: float
    ) -> List[SimulationResult]:
        """
        Walk-Forwardシミュレーションを実行
        
        学習期間でパラメータを最適化し、
        検証期間でパフォーマンスを評価する
        """
        results = []
        
        # レースを日付順にソート
        sorted_races = sorted(races, key=lambda r: r.race_date)
        
        if not sorted_races:
            return results
        
        start_date = sorted_races[0].race_date
        end_date = sorted_races[-1].race_date
        
        current_date = start_date + timedelta(days=self.train_period)
        
        while current_date + timedelta(days=self.test_period) <= end_date:
            # 学習期間
            train_start = current_date - timedelta(days=self.train_period)
            train_end = current_date
            
            # 検証期間
            test_start = current_date
            test_end = current_date + timedelta(days=self.test_period)
            
            # データ分割
            train_races = [r for r in sorted_races if train_start <= r.race_date < train_end]
            test_races = [r for r in sorted_races if test_start <= r.race_date < test_end]
            
            if train_races and test_races:
                # 学習期間でパラメータ最適化（オプション）
                optimized_params = self._optimize_params(train_races, strategy)
                
                # 検証期間でシミュレーション
                result = SimpleSimulation().run(
                    test_races, strategy, fund_manager, initial_fund
                )
                result.period = {
                    "train_start": train_start.isoformat(),
                    "train_end": train_end.isoformat(),
                    "test_start": test_start.isoformat(),
                    "test_end": test_end.isoformat()
                }
                results.append(result)
            
            # 次の期間へ
            current_date += timedelta(days=self.step)
        
        return results
    
    def _optimize_params(self, train_races: List[Race], strategy: BaseStrategy) -> Dict:
        """学習期間のデータでパラメータを最適化"""
        # グリッドサーチやベイズ最適化等
        pass
```

**Walk-Forward図解**:

```
時間軸 ─────────────────────────────────────────────────────►

期間1: [====学習期間====][検証]
期間2:        [====学習期間====][検証]
期間3:               [====学習期間====][検証]
期間4:                      [====学習期間====][検証]
```

---

## 5. 評価指標計算

### 5.1 収益指標

```python
class MetricsCalculator:
    """評価指標計算クラス"""
    
    def calculate_roi(self, total_invested: float, total_payout: float) -> float:
        """
        ROI（投資収益率）を計算
        
        ROI = (総払戻 / 総投資) × 100
        """
        if total_invested == 0:
            return 0.0
        return (total_payout / total_invested) * 100
    
    def calculate_cagr(
        self,
        initial_fund: float,
        final_fund: float,
        years: float
    ) -> float:
        """
        CAGR（年平均成長率）を計算
        
        CAGR = (最終資金 / 初期資金)^(1/年数) - 1
        """
        if initial_fund <= 0 or final_fund <= 0 or years <= 0:
            return 0.0
        return (final_fund / initial_fund) ** (1 / years) - 1
```

**ROI計算式**:
$$ROI = \frac{\text{総払戻金}}{\text{総投資額}} \times 100$$

**CAGR計算式**:
$$CAGR = \left(\frac{V_f}{V_i}\right)^{\frac{1}{n}} - 1$$

### 5.2 リスク指標

```python
def calculate_max_drawdown(self, fund_history: List[float]) -> Tuple[float, int]:
    """
    最大ドローダウンを計算
    
    Returns:
        (最大DD率(%), 最大DD期間(レース数))
    """
    if not fund_history:
        return 0.0, 0
    
    peak = fund_history[0]
    max_dd = 0.0
    max_dd_period = 0
    current_dd_start = 0
    
    for i, fund in enumerate(fund_history):
        if fund > peak:
            peak = fund
            current_dd_start = i
        
        dd = (peak - fund) / peak * 100
        if dd > max_dd:
            max_dd = dd
            max_dd_period = i - current_dd_start
    
    return max_dd, max_dd_period

def calculate_sharpe_ratio(
    self,
    returns: List[float],
    risk_free_rate: float = 0.0
) -> float:
    """
    シャープレシオを計算
    
    Sharpe = (平均リターン - 無リスク金利) / リターンの標準偏差
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    
    if std_return == 0:
        return 0.0
    
    return (mean_return - risk_free_rate) / std_return

def calculate_sortino_ratio(
    self,
    returns: List[float],
    risk_free_rate: float = 0.0
) -> float:
    """
    ソルティノレシオを計算
    
    下方リスクのみを考慮したリスク調整後リターン
    """
    if not returns:
        return 0.0
    
    mean_return = np.mean(returns)
    negative_returns = [r for r in returns if r < 0]
    
    if not negative_returns:
        return float('inf')
    
    downside_std = np.std(negative_returns)
    
    if downside_std == 0:
        return float('inf')
    
    return (mean_return - risk_free_rate) / downside_std

def calculate_var(
    self,
    returns: List[float],
    confidence: float = 0.95
) -> float:
    """
    VaR（Value at Risk）を計算
    
    指定した信頼水準での最大損失額
    """
    if not returns:
        return 0.0
    
    return np.percentile(returns, (1 - confidence) * 100)

def calculate_cvar(
    self,
    returns: List[float],
    confidence: float = 0.95
) -> float:
    """
    CVaR（Conditional VaR）を計算
    
    VaRを超えた場合の期待損失額
    """
    if not returns:
        return 0.0
    
    var = self.calculate_var(returns, confidence)
    tail_returns = [r for r in returns if r <= var]
    
    if not tail_returns:
        return var
    
    return np.mean(tail_returns)
```

**シャープレシオ計算式**:
$$SR = \frac{R_p - R_f}{\sigma_p}$$

ここで:
- $R_p$: ポートフォリオの平均リターン
- $R_f$: 無リスク金利
- $\sigma_p$: リターンの標準偏差

**最大ドローダウン計算式**:
$$MDD = \max_{t \in [0,T]} \left( \frac{\max_{s \in [0,t]} V_s - V_t}{\max_{s \in [0,t]} V_s} \right)$$

### 5.3 破産確率計算

```python
def calculate_bankruptcy_probability(
    self,
    mc_final_funds: np.ndarray,
    bankruptcy_threshold: float
) -> float:
    """
    破産確率を計算（モンテカルロ結果から）
    
    Args:
        mc_final_funds: モンテカルロ試行の最終資金配列
        bankruptcy_threshold: 破産とみなす資金（初期資金の10%等）
    
    Returns:
        破産確率（%）
    """
    num_bankruptcies = np.sum(mc_final_funds < bankruptcy_threshold)
    return (num_bankruptcies / len(mc_final_funds)) * 100
```

---

## 6. Go/No-Go判定アルゴリズム

```python
@dataclass
class GoNoGoDecision:
    """Go/No-Go判定結果"""
    decision: bool
    go_reasons: List[str]
    nogo_reasons: List[str]

class GoNoGoJudge:
    """Go/No-Go判定クラス"""
    
    # Go条件（全て満たす必要あり）
    GO_CONDITIONS = {
        'bankruptcy_prob_max': 5.0,       # 破産確率 5%以下
        'roi_min': 150.0,                  # ROI 150%以上
        'max_drawdown_max': 50.0,          # 最大DD 50%以下
        'yearly_positive_ratio': 0.67,     # 3年中2年以上でROI>100%
    }
    
    # No-Go条件（1つでも該当でNo-Go）
    NOGO_CONDITIONS = {
        'bankruptcy_prob_min': 10.0,       # 破産確率 10%以上
        'roi_max': 120.0,                  # ROI 120%未満
        'max_consecutive_losses_min': 30,  # 30連敗以上
    }
    
    def judge(self, metrics: SimulationMetrics) -> GoNoGoDecision:
        """Go/No-Go判定を実行"""
        go_reasons = []
        nogo_reasons = []
        
        # Go条件チェック
        if metrics.bankruptcy_prob <= self.GO_CONDITIONS['bankruptcy_prob_max']:
            go_reasons.append(
                f"破産確率 {metrics.bankruptcy_prob:.1f}% <= {self.GO_CONDITIONS['bankruptcy_prob_max']}%"
            )
        
        if metrics.roi >= self.GO_CONDITIONS['roi_min']:
            go_reasons.append(
                f"ROI {metrics.roi:.1f}% >= {self.GO_CONDITIONS['roi_min']}%"
            )
        
        if metrics.max_drawdown <= self.GO_CONDITIONS['max_drawdown_max']:
            go_reasons.append(
                f"最大DD {metrics.max_drawdown:.1f}% <= {self.GO_CONDITIONS['max_drawdown_max']}%"
            )
        
        # No-Go条件チェック
        if metrics.bankruptcy_prob >= self.NOGO_CONDITIONS['bankruptcy_prob_min']:
            nogo_reasons.append(
                f"破産確率 {metrics.bankruptcy_prob:.1f}% >= {self.NOGO_CONDITIONS['bankruptcy_prob_min']}%"
            )
        
        if metrics.roi < self.NOGO_CONDITIONS['roi_max']:
            nogo_reasons.append(
                f"ROI {metrics.roi:.1f}% < {self.NOGO_CONDITIONS['roi_max']}%"
            )
        
        if metrics.max_consecutive_losses >= self.NOGO_CONDITIONS['max_consecutive_losses_min']:
            nogo_reasons.append(
                f"最大連敗 {metrics.max_consecutive_losses} >= {self.NOGO_CONDITIONS['max_consecutive_losses_min']}"
            )
        
        # 判定
        # No-Go条件に1つでも該当 → No-Go
        # Go条件を全て満たす → Go
        if nogo_reasons:
            decision = False
        elif len(go_reasons) >= 3:  # 主要3条件を満たす
            decision = True
        else:
            decision = False
        
        return GoNoGoDecision(
            decision=decision,
            go_reasons=go_reasons,
            nogo_reasons=nogo_reasons
        )
```

---

## 7. 戦略ファクトリー

```python
class StrategyFactory:
    """戦略クラスのファクトリー"""
    
    STRATEGY_MAP = {
        # 単勝戦略
        'favorite_win': FavoriteWinStrategy,
        'longshot_win': LongshotWinStrategy,
        'value_win': ValueWinStrategy,
        
        # 複勝戦略
        'favorite_place': FavoritePlaceStrategy,
        'longshot_place': LongshotPlaceStrategy,
        
        # 馬連戦略
        'favorite_quinella': FavoriteQuinellaStrategy,
        'favorite_longshot_quinella': FavoriteLongshotQuinellaStrategy,
        'box_quinella': BoxQuinellaStrategy,
        
        # ワイド戦略
        'favorite_wide': FavoriteWideStrategy,
        'favorite_longshot_wide': FavoriteLongshotWideStrategy,
        'box_wide': BoxWideStrategy,
        
        # 三連複戦略
        'favorite_trio': FavoriteTrioStrategy,
        'favorite2_longshot_trio': Favorite2LongshotTrioStrategy,
        'formation_trio': FormationTrioStrategy,
    }
    
    @classmethod
    def create(cls, name: str, params: Dict[str, Any]) -> BaseStrategy:
        """戦略名からインスタンスを生成"""
        if name not in cls.STRATEGY_MAP:
            raise ValueError(f"Unknown strategy: {name}")
        
        strategy_class = cls.STRATEGY_MAP[name]
        return strategy_class(params)
    
    @classmethod
    def create_composite(
        cls,
        strategies_config: List[Dict[str, Any]]
    ) -> CompositeStrategy:
        """複合戦略を生成"""
        strategies = []
        for config in strategies_config:
            strategy = cls.create(config['name'], config.get('params', {}))
            weight = config.get('weight', 1.0)
            strategies.append((strategy, weight))
        
        return CompositeStrategy(strategies)
```

---

## 8. 付録

### 8.1 戦略一覧表

| 戦略名 | 馬券種 | 説明 | 推奨パラメータ |
|--------|-------|------|---------------|
| favorite_win | 単勝 | 予測1位の単勝 | top_n=1 |
| longshot_win | 単勝 | 穴馬候補の単勝 | upset_threshold=0.5 |
| value_win | 単勝 | 期待値ベース | min_ev=1.2 |
| favorite_place | 複勝 | 予測上位の複勝 | top_n=2 |
| favorite_quinella | 馬連 | 予測上位2頭 | - |
| favorite_longshot_quinella | 馬連 | 本命-穴馬流し | max_counterparts=3 |
| box_quinella | 馬連 | ボックス | box_size=4 |
| favorite_trio | 三連複 | 予測上位3頭 | - |
| favorite2_longshot_trio | 三連複 | 2頭軸流し | max_counterparts=3 |
| formation_trio | 三連複 | フォーメーション | first_leg=[1,2] |

### 8.2 参考文献

- Kelly, J. L. (1956). "A New Interpretation of Information Rate"
- Thorp, E. O. (2006). "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market"

---

**文書情報**
- 作成日: 2026-01-21
- バージョン: 1.0.0
- 関連文書: [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md), [DATA_DESIGN.md](./DATA_DESIGN.md)
