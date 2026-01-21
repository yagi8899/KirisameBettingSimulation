# データ設計書（Data Design Document）

## 1. 概要

本ドキュメントは、競馬賭けシミュレーションシステムで扱うデータの構造、フォーマット、データフローを定義する。

---

## 2. 入力データ仕様

### 2.1 予測結果ファイル（TSV形式）

システムへの唯一の入力データソース。予測システムから出力されたTSV形式のファイル。

#### 2.1.1 ファイル仕様

| 項目 | 仕様 |
|------|------|
| ファイル形式 | TSV（Tab-Separated Values） |
| 文字コード | UTF-8 |
| 改行コード | LF または CRLF |
| ヘッダー | 1行目に必須 |
| データ行 | 2行目以降 |

#### 2.1.2 必須カラム

| カラム名 | データ型 | 説明 | 例 |
|----------|---------|------|-----|
| 競馬場 | string | 競馬場名 | "東京", "中山" |
| 開催年 | int | 西暦年 | 2025 |
| 開催日 | int | 開催日（回・日形式） | 0101（1回1日） |
| レース番号 | int | レース番号（1-12） | 11 |
| 芝ダ区分 | string | コース種別 | "芝", "ダート" |
| 距離 | int | 距離（メートル） | 1600 |
| 馬番 | int | 馬番号（1-18） | 5 |
| 馬名 | string | 馬の名前 | "キタサンブラック" |
| 単勝オッズ | float | 単勝オッズ | 2.5 |
| 人気順 | int | 人気順位 | 1 |
| 確定着順 | int | 確定した着順 | 1 |
| 予測順位 | int | 予測された順位 | 1 |
| 予測スコア | float | 予測スコア（0-1） | 0.85 |

#### 2.1.3 オプションカラム

| カラム名 | データ型 | 説明 | デフォルト |
|----------|---------|------|-----------|
| 穴馬確率 | float | 穴馬である確率（0-1） | 0.0 |
| 穴馬候補 | bool/int | 穴馬候補フラグ | False |
| 実際の穴馬 | bool/int | 実際に穴馬だったか | False |
| 複勝下限オッズ | float | 複勝オッズ下限 | null |
| 複勝上限オッズ | float | 複勝オッズ上限 | null |
| 馬連オッズ_{馬番} | float | 馬連オッズ | null |
| ワイドオッズ_{馬番} | float | ワイドオッズ | null |
| 馬単オッズ_{馬番} | float | 馬単オッズ | null |
| 三連複オッズ | float | 三連複オッズ | null |

#### 2.1.4 サンプルデータ

```tsv
競馬場	開催年	開催日	レース番号	芝ダ区分	距離	馬番	馬名	単勝オッズ	人気順	確定着順	予測順位	予測スコア	穴馬確率	穴馬候補
東京	2025	0501	11	芝	1600	1	サンプルホース1	15.3	5	3	4	0.72	0.35	0
東京	2025	0501	11	芝	1600	2	サンプルホース2	3.2	1	1	1	0.91	0.05	0
東京	2025	0501	11	芝	1600	3	サンプルホース3	8.7	3	2	2	0.85	0.15	0
東京	2025	0501	11	芝	1600	4	サンプルホース4	45.2	10	8	6	0.58	0.72	1
```

---

## 3. データモデル定義

### 3.1 Horse（馬データクラス）

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Horse:
    """馬データを表すイミュータブルなデータクラス"""
    
    # 基本情報
    number: int                    # 馬番（1-18）
    name: str                      # 馬名
    
    # オッズ・人気
    odds: float                    # 単勝オッズ
    popularity: int                # 人気順
    
    # 結果
    actual_rank: int               # 確定着順（0=未確定, 99=失格等）
    
    # 予測情報
    predicted_rank: int            # 予測順位
    predicted_score: float         # 予測スコア（0.0-1.0）
    
    # 穴馬情報
    upset_prob: float = 0.0        # 穴馬確率（0.0-1.0）
    is_upset_candidate: bool = False  # 穴馬候補フラグ
    is_actual_upset: bool = False  # 実際に穴馬だったか
    
    # 複勝オッズ
    place_odds_min: Optional[float] = None  # 複勝オッズ下限
    place_odds_max: Optional[float] = None  # 複勝オッズ上限
    
    def __post_init__(self):
        """バリデーション"""
        if not 1 <= self.number <= 18:
            raise ValueError(f"馬番は1-18の範囲: {self.number}")
        if self.odds <= 0:
            raise ValueError(f"オッズは正の数: {self.odds}")
        if not 0.0 <= self.predicted_score <= 1.0:
            raise ValueError(f"予測スコアは0-1の範囲: {self.predicted_score}")
    
    @property
    def expected_value(self) -> float:
        """期待値（単勝）を計算"""
        return self.predicted_score * self.odds
    
    @property
    def is_favorite(self) -> bool:
        """本命馬かどうか（予測1位）"""
        return self.predicted_rank == 1
    
    @property
    def is_in_frame(self) -> bool:
        """3着以内に入ったか"""
        return 1 <= self.actual_rank <= 3
```

### 3.2 Race（レースデータクラス）

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date

@dataclass
class Race:
    """レースデータを表すデータクラス"""
    
    # レース識別情報
    track: str                     # 競馬場
    year: int                      # 開催年
    kaisai_date: int               # 開催日（例: 0501 = 5回1日）
    race_number: int               # レース番号（1-12）
    
    # レース条件
    surface: str                   # 芝/ダート
    distance: int                  # 距離（メートル）
    
    # 出走馬リスト
    horses: List[Horse] = field(default_factory=list)
    
    # 払戻情報
    payouts: Dict[str, Dict] = field(default_factory=dict)
    
    # オプション情報
    race_name: Optional[str] = None     # レース名
    grade: Optional[str] = None         # グレード（G1, G2等）
    weather: Optional[str] = None       # 天候
    track_condition: Optional[str] = None  # 馬場状態
    
    @property
    def race_id(self) -> str:
        """レース一意識別子"""
        return f"{self.track}_{self.year}_{self.kaisai_date:04d}_{self.race_number:02d}"
    
    @property
    def race_date(self) -> date:
        """レース日付をdateオブジェクトで取得"""
        # kaisai_dateから実際の日付を算出（要実装）
        pass
    
    @property
    def horse_count(self) -> int:
        """出走頭数"""
        return len(self.horses)
    
    def get_horse_by_number(self, number: int) -> Optional[Horse]:
        """馬番から馬を取得"""
        for horse in self.horses:
            if horse.number == number:
                return horse
        return None
    
    def get_horses_by_predicted_rank(self, max_rank: int) -> List[Horse]:
        """予測順位上位N頭を取得"""
        return sorted(
            [h for h in self.horses if h.predicted_rank <= max_rank],
            key=lambda h: h.predicted_rank
        )
    
    def get_upset_candidates(self) -> List[Horse]:
        """穴馬候補を取得"""
        return [h for h in self.horses if h.is_upset_candidate]
    
    def get_winner(self) -> Optional[Horse]:
        """1着馬を取得"""
        for horse in self.horses:
            if horse.actual_rank == 1:
                return horse
        return None
    
    def get_frame_horses(self) -> List[Horse]:
        """3着以内の馬を取得"""
        return sorted(
            [h for h in self.horses if h.is_in_frame],
            key=lambda h: h.actual_rank
        )
```

### 3.3 Ticket（馬券データクラス）

```python
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum

class TicketType(Enum):
    """馬券種別"""
    WIN = "win"           # 単勝
    PLACE = "place"       # 複勝
    QUINELLA = "quinella" # 馬連
    WIDE = "wide"         # ワイド
    EXACTA = "exacta"     # 馬単
    TRIO = "trio"         # 三連複
    TRIFECTA = "trifecta" # 三連単

@dataclass
class Ticket:
    """馬券データを表すデータクラス"""
    
    ticket_type: TicketType        # 馬券種別
    horse_numbers: Tuple[int, ...] # 馬番（タプルで不変）
    odds: float                    # 購入時オッズ
    amount: int                    # 賭け金（円）
    
    # 購入根拠（オプション）
    strategy_name: str = ""        # 使用戦略名
    expected_value: float = 0.0    # 期待値
    confidence: float = 0.0        # 信頼度
    
    def __post_init__(self):
        """バリデーション"""
        if self.amount < 100:
            raise ValueError(f"最小賭け金は100円: {self.amount}")
        if self.amount % 100 != 0:
            raise ValueError(f"賭け金は100円単位: {self.amount}")
        if self.odds <= 0:
            raise ValueError(f"オッズは正の数: {self.odds}")
    
    @property
    def potential_payout(self) -> int:
        """想定払戻金"""
        return int(self.amount * self.odds)
    
    @property
    def ticket_key(self) -> str:
        """馬券の一意キー"""
        numbers = "-".join(map(str, sorted(self.horse_numbers)))
        return f"{self.ticket_type.value}_{numbers}"
    
    def is_hit(self, result_numbers: List[int]) -> bool:
        """的中判定（簡易版、詳細はBetEvaluatorで実装）"""
        # 馬券種別ごとの判定ロジック
        pass
```

### 3.4 BetRecord（購入記録データクラス）

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class BetRecord:
    """1回の購入記録"""
    
    # レース情報
    race_id: str                   # レースID
    race_date: datetime            # レース日時
    
    # 馬券情報
    ticket: Ticket                 # 購入馬券
    
    # 結果
    is_hit: bool = False           # 的中フラグ
    payout: int = 0                # 払戻金（円）
    
    # 資金状況
    fund_before: float = 0.0       # 購入前資金
    fund_after: float = 0.0        # 購入後資金
    
    @property
    def profit(self) -> int:
        """損益"""
        return self.payout - self.ticket.amount
    
    @property
    def roi(self) -> float:
        """ROI"""
        if self.ticket.amount == 0:
            return 0.0
        return self.payout / self.ticket.amount
```

### 3.5 SimulationResult（シミュレーション結果データクラス）

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class SimulationMetrics:
    """シミュレーション評価指標"""
    
    # 収益指標
    total_invested: float = 0.0    # 総投資額
    total_payout: float = 0.0      # 総払戻額
    net_profit: float = 0.0        # 純利益
    roi: float = 0.0               # ROI（%）
    cagr: float = 0.0              # 複利成長率
    
    # リスク指標
    max_drawdown: float = 0.0      # 最大ドローダウン（%）
    max_drawdown_period: int = 0   # 最大DD期間（レース数）
    bankruptcy_prob: float = 0.0   # 破産確率（%）
    sharpe_ratio: float = 0.0      # シャープレシオ
    sortino_ratio: float = 0.0     # ソルティノレシオ
    var_95: float = 0.0            # VaR（95%）
    cvar_95: float = 0.0           # CVaR（95%）
    
    # 的中指標
    total_bets: int = 0            # 総賭け回数
    total_hits: int = 0            # 的中回数
    hit_rate: float = 0.0          # 的中率（%）
    recovery_rate: float = 0.0     # 回収率（%）
    max_consecutive_losses: int = 0 # 最大連敗数
    avg_hit_interval: float = 0.0  # 平均的中間隔

@dataclass
class SimulationResult:
    """シミュレーション結果"""
    
    # 基本情報
    simulation_id: str             # シミュレーションID
    simulation_type: str           # シミュレーション種別
    executed_at: datetime = field(default_factory=datetime.now)
    
    # 設定情報
    config: Dict[str, Any] = field(default_factory=dict)
    
    # 資金推移
    initial_fund: float = 0.0      # 初期資金
    final_fund: float = 0.0        # 最終資金
    fund_history: List[float] = field(default_factory=list)
    
    # 購入履歴
    bet_history: List[BetRecord] = field(default_factory=list)
    
    # 評価指標
    metrics: SimulationMetrics = field(default_factory=SimulationMetrics)
    
    # Go/No-Go判定
    go_decision: bool = False
    go_reasons: List[str] = field(default_factory=list)
    nogo_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（JSON出力用）"""
        pass
    
    def to_summary(self) -> str:
        """サマリーテキスト生成"""
        pass
```

### 3.6 MonteCarloResult（モンテカルロ結果データクラス）

```python
from dataclasses import dataclass, field
from typing import List, Dict
import numpy as np

@dataclass
class MonteCarloResult:
    """モンテカルロシミュレーション結果"""
    
    # 基本情報
    num_trials: int                # 試行回数
    random_seed: int               # ランダムシード
    
    # 最終資金の分布
    final_funds: np.ndarray        # 各試行の最終資金
    
    # 統計情報
    mean_final_fund: float = 0.0   # 平均最終資金
    median_final_fund: float = 0.0 # 中央値最終資金
    std_final_fund: float = 0.0    # 標準偏差
    
    # パーセンタイル
    percentile_5: float = 0.0      # 5%分位点
    percentile_25: float = 0.0     # 25%分位点
    percentile_75: float = 0.0     # 75%分位点
    percentile_95: float = 0.0     # 95%分位点
    
    # 確率指標
    bankruptcy_probability: float = 0.0    # 破産確率
    target_achievement_prob: float = 0.0   # 目標達成確率
    expected_days_to_target: float = 0.0   # 期待到達日数
    
    # 全試行の資金推移（オプション）
    all_fund_histories: List[List[float]] = field(default_factory=list)
```

---

## 4. 払戻データ構造

### 4.1 払戻情報スキーマ

```python
PayoutSchema = {
    "win": {
        # 単勝
        "horse_number": int,       # 馬番
        "payout": int              # 払戻金（100円あたり）
    },
    "place": [
        # 複勝（最大3頭）
        {
            "horse_number": int,
            "payout": int
        }
    ],
    "quinella": {
        # 馬連
        "horse_numbers": [int, int],
        "payout": int
    },
    "wide": [
        # ワイド（最大3組）
        {
            "horse_numbers": [int, int],
            "payout": int
        }
    ],
    "exacta": {
        # 馬単
        "horse_numbers": [int, int],  # [1着, 2着]
        "payout": int
    },
    "trio": {
        # 三連複
        "horse_numbers": [int, int, int],
        "payout": int
    },
    "trifecta": {
        # 三連単
        "horse_numbers": [int, int, int],  # [1着, 2着, 3着]
        "payout": int
    }
}
```

---

## 5. 設定ファイル構造（YAML）

### 5.1 メイン設定スキーマ

```yaml
# config/simulation_config.yaml

# シミュレーション基本設定
simulation:
  type: "simple"           # simple / monte_carlo / walk_forward
  initial_fund: 100000     # 初期資金（円）
  random_seed: 42          # 乱数シード（再現性確保）

# モンテカルロ設定（type: monte_carloの場合）
monte_carlo:
  num_trials: 10000        # 試行回数
  method: "bootstrap"      # bootstrap / probability_based
  confidence_level: 0.95   # 信頼水準

# Walk-Forward設定（type: walk_forwardの場合）
walk_forward:
  train_period_days: 180   # 学習期間（日）
  test_period_days: 30     # 検証期間（日）
  step_days: 30            # スライド幅（日）

# 戦略設定
strategy:
  name: "favorite_win"     # 戦略名
  params:                  # 戦略パラメータ（戦略ごとに異なる）
    top_n: 1               # 予測上位N頭
    min_expected_value: 1.0

# 複合戦略設定
composite_strategy:
  enabled: false
  strategies:
    - name: "favorite_win"
      weight: 0.5
      params:
        top_n: 1
    - name: "longshot_place"
      weight: 0.5
      params:
        upset_threshold: 0.6

# 資金管理設定
fund_management:
  method: "kelly"          # fixed / percentage / kelly
  params:
    # fixed
    bet_amount: 1000       # 1点あたり賭け金（円）
    
    # percentage
    bet_percentage: 0.02   # 資金の2%
    
    # kelly
    kelly_fraction: 0.25   # ケリー基準の25%
    
  constraints:
    min_bet: 100           # 最小賭け金
    max_bet_per_ticket: 5000      # 1点上限
    max_bet_per_race: 10000       # 1レース上限
    max_bet_per_day: 50000        # 1日上限
    stop_loss_threshold: 0.5      # 損切りライン（初期資金の50%）

# レースフィルタ設定
race_filter:
  # 基本フィルタ
  min_horse_count: 12      # 最小出走頭数
  min_confidence: 0.6      # 最小レース信頼度
  
  # 条件フィルタ
  tracks:
    mode: "whitelist"      # whitelist / blacklist / tier
    list: ["東京", "中山", "阪神", "京都"]
    tiers:
      tier1: ["東京", "中山"]      # 全額
      tier2: ["阪神", "京都"]      # 80%
      tier3: ["中京", "小倉"]      # 60%
  
  surface: null            # null=両方, "芝", "ダート"
  distance:
    min: 1200
    max: 3600
  
  # 期待値フィルタ
  min_expected_value: 1.0
  
  # 見送り条件
  skip_conditions:
    maiden_race: true      # 新馬戦・未勝利戦
    bad_weather: true      # 荒天時
    no_upset_candidate: false  # 穴馬候補なし

# 出力設定
output:
  directory: "./output"
  formats:
    json: true
    csv: true
    txt: true
  charts:
    enabled: true
    format: "png"          # png / html / both
    dpi: 150

# ロギング設定
logging:
  level: "INFO"            # DEBUG / INFO / WARNING / ERROR
  file: "./logs/simulation.log"
```

---

## 6. 出力ファイル仕様

### 6.1 simulation_result.json

```json
{
  "simulation_id": "sim_20260121_143052",
  "simulation_type": "monte_carlo",
  "executed_at": "2026-01-21T14:30:52",
  "config": {
    "initial_fund": 100000,
    "strategy": "favorite_win",
    "fund_management": "kelly"
  },
  "summary": {
    "initial_fund": 100000,
    "final_fund": 135420,
    "net_profit": 35420,
    "roi": 135.42,
    "total_bets": 520,
    "total_hits": 156,
    "hit_rate": 30.0,
    "max_drawdown": 18.5
  },
  "metrics": {
    "revenue": {
      "roi": 135.42,
      "cagr": 12.5,
      "net_profit": 35420
    },
    "risk": {
      "max_drawdown": 18.5,
      "bankruptcy_prob": 2.3,
      "sharpe_ratio": 1.45,
      "var_95": -15000
    },
    "hit": {
      "hit_rate": 30.0,
      "recovery_rate": 135.42,
      "max_consecutive_losses": 12
    }
  },
  "go_decision": {
    "decision": true,
    "go_reasons": [
      "破産確率 2.3% < 5%",
      "ROI 135.42% > 150%",
      "最大DD 18.5% < 50%"
    ],
    "nogo_reasons": []
  },
  "monte_carlo": {
    "num_trials": 10000,
    "mean_final_fund": 142350,
    "median_final_fund": 135420,
    "percentile_5": 78500,
    "percentile_95": 215600,
    "bankruptcy_probability": 2.3
  }
}
```

### 6.2 fund_history.csv

```csv
date,race_id,race_number,fund_before,bet_amount,payout,fund_after,cumulative_profit,drawdown
2025-01-05,東京_2025_0101_11,1,100000,1000,0,99000,-1000,1.0
2025-01-05,東京_2025_0101_12,2,99000,1000,3200,101200,1200,0.0
2025-01-06,中山_2025_0101_11,3,101200,1200,0,100000,0,1.2
```

### 6.3 bet_history.csv

```csv
date,race_id,ticket_type,horse_numbers,odds,amount,is_hit,payout,profit,strategy,expected_value
2025-01-05,東京_2025_0101_11,win,5,3.2,1000,false,0,-1000,favorite_win,1.28
2025-01-05,東京_2025_0101_12,win,2,2.8,1000,true,2800,1800,favorite_win,1.42
2025-01-06,中山_2025_0101_11,quinella,3-7,12.5,1200,false,0,-1200,favorite_quinella,1.15
```

### 6.4 simulation_summary.txt

```
================================================================================
競馬賭けシミュレーション結果サマリー
================================================================================

■ 実行情報
  シミュレーションID: sim_20260121_143052
  実行日時: 2026-01-21 14:30:52
  シミュレーション種別: モンテカルロ（10,000試行）

■ 設定情報
  初期資金: 100,000円
  戦略: 予測1位単勝（favorite_win）
  資金管理: ケリー基準（fraction: 0.25）

■ 収益指標
  最終資金: 135,420円
  純利益: +35,420円
  ROI: 135.42%
  年率リターン: 42.5%

■ リスク指標
  最大ドローダウン: 18.5%
  破産確率: 2.3%
  シャープレシオ: 1.45
  VaR (95%): -15,000円

■ 的中指標
  総賭け回数: 520回
  的中回数: 156回
  的中率: 30.0%
  回収率: 135.42%
  最大連敗: 12連敗

■ Go/No-Go判定
  判定結果: ✅ GO

  Go条件クリア:
    ✅ 破産確率 2.3% < 5%
    ✅ ROI 135.42% >= 150%
    ✅ 最大ドローダウン 18.5% < 50%

================================================================================
```

---

## 7. データフロー

### 7.1 処理フロー図

```
┌─────────────────┐
│ 予測結果TSV     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DataLoader      │───► Horse, Raceオブジェクト生成
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ RaceFilter      │───► フィルタ条件に合うレースを選択
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ StrategyEngine  │───► 各レースで購入馬券を決定
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FundManager     │───► 賭け金を計算
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BetEvaluator    │───► 的中判定・払戻計算
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MetricsCalc     │───► 評価指標計算
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SimulationResult│
└────────┬────────┘
         │
    ┌────┴────┬────────────┐
    ▼         ▼            ▼
┌───────┐ ┌───────┐  ┌──────────┐
│ JSON  │ │ CSV   │  │ Charts   │
└───────┘ └───────┘  └──────────┘
```

### 7.2 データ変換マトリクス

| 入力 | 処理 | 出力 |
|------|------|------|
| TSV行 | DataLoader.parse_row() | Horse |
| Horse[] | DataLoader.aggregate_race() | Race |
| Race | RaceFilter.apply() | Race or None |
| Race | Strategy.generate_tickets() | Ticket[] |
| Ticket | FundManager.calculate_amount() | Ticket (with amount) |
| Ticket, Race | BetEvaluator.evaluate() | BetRecord |
| BetRecord[] | MetricsCalculator.calculate() | SimulationMetrics |

---

## 8. データバリデーション

### 8.1 入力バリデーションルール

| フィールド | ルール | エラー時の動作 |
|-----------|--------|---------------|
| 競馬場 | 有効な競馬場名 | エラーログ、行スキップ |
| 開催年 | 2000-2100 | エラーログ、行スキップ |
| レース番号 | 1-12 | エラーログ、行スキップ |
| 馬番 | 1-18 | エラーログ、行スキップ |
| 単勝オッズ | > 1.0 | デフォルト値設定 |
| 予測スコア | 0.0-1.0 | クリップ処理 |

### 8.2 整合性チェック

| チェック項目 | 条件 | 対応 |
|-------------|------|------|
| 同一レース内の馬番重複 | 馬番がユニーク | 警告ログ、後勝ち |
| 予測順位の連続性 | 1からの連番 | 警告ログ、継続 |
| 確定着順の妥当性 | 出走頭数以内 | エラーログ、行スキップ |

---

## 9. 付録

### 9.1 競馬場コード一覧

| コード | 競馬場名 | Tier |
|--------|---------|------|
| 01 | 札幌 | 3 |
| 02 | 函館 | 3 |
| 03 | 福島 | 3 |
| 04 | 新潟 | 3 |
| 05 | 東京 | 1 |
| 06 | 中山 | 1 |
| 07 | 中京 | 2 |
| 08 | 京都 | 1 |
| 09 | 阪神 | 1 |
| 10 | 小倉 | 3 |

### 9.2 馬券種別コード

| コード | 名称 | 英名 |
|--------|------|------|
| win | 単勝 | Win |
| place | 複勝 | Place |
| quinella | 馬連 | Quinella |
| wide | ワイド | Wide |
| exacta | 馬単 | Exacta |
| trio | 三連複 | Trio |
| trifecta | 三連単 | Trifecta |

---

**文書情報**
- 作成日: 2026-01-21
- バージョン: 1.0.0
- 関連文書: [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md), [API_INTERFACE.md](./API_INTERFACE.md)
