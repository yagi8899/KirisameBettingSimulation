# API・インターフェース設計書（API & Interface Design Document）

## 1. 概要

本ドキュメントは、競馬賭けシミュレーションシステムの各モジュールが提供するPublic API、設定ファイルスキーマ、CLIインターフェースを定義する。

---

## 2. モジュールAPI仕様

### 2.1 DataLoader モジュール

#### 2.1.1 DataLoader クラス

```python
class DataLoader:
    """予測結果TSVファイルを読み込み、Race/Horseオブジェクトに変換"""
    
    def __init__(
        self,
        required_columns: Optional[List[str]] = None,
        encoding: str = "utf-8"
    ):
        """
        Args:
            required_columns: 必須カラムのリスト（Noneの場合はデフォルト使用）
            encoding: ファイルエンコーディング
        """
        pass
    
    def load(self, filepath: Union[str, Path]) -> List[Race]:
        """
        TSVファイルを読み込み、Raceオブジェクトのリストを返す
        
        Args:
            filepath: TSVファイルのパス
            
        Returns:
            Raceオブジェクトのリスト
            
        Raises:
            DataLoadError: ファイル読み込みエラー
            InvalidFormatError: フォーマット不正
        """
        pass
    
    def load_multiple(self, filepaths: List[Union[str, Path]]) -> List[Race]:
        """
        複数のTSVファイルを読み込み、結合して返す
        
        Args:
            filepaths: TSVファイルパスのリスト
            
        Returns:
            全ファイルのRaceを結合したリスト
        """
        pass
    
    def validate(self, filepath: Union[str, Path]) -> ValidationResult:
        """
        TSVファイルのバリデーションのみ実行
        
        Args:
            filepath: TSVファイルのパス
            
        Returns:
            ValidationResult(is_valid, errors, warnings)
        """
        pass
```

#### 2.1.2 使用例

```python
from betting_simulation.core import DataLoader

# 基本的な使用
loader = DataLoader()
races = loader.load("data/input/predictions_2025.tsv")

# バリデーションのみ
result = loader.validate("data/input/predictions_2025.tsv")
if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")
```

---

### 2.2 RaceFilter モジュール

#### 2.2.1 RaceFilter クラス

```python
class RaceFilter:
    """レース選択フィルタ"""
    
    def __init__(self, config: FilterConfig):
        """
        Args:
            config: フィルタ設定
        """
        pass
    
    def apply(self, races: List[Race]) -> List[Race]:
        """
        フィルタ条件を適用し、条件を満たすレースのみ返す
        
        Args:
            races: フィルタ対象のレースリスト
            
        Returns:
            フィルタ後のレースリスト
        """
        pass
    
    def should_skip(self, race: Race) -> Tuple[bool, Optional[str]]:
        """
        レースを見送るべきか判定
        
        Args:
            race: 判定対象のレース
            
        Returns:
            (見送りフラグ, 見送り理由)
        """
        pass
    
    def get_tier(self, track: str) -> int:
        """
        競馬場のTierを取得
        
        Args:
            track: 競馬場名
            
        Returns:
            Tier番号（1-3）
        """
        pass

@dataclass
class FilterConfig:
    """フィルタ設定"""
    min_horse_count: int = 12
    min_confidence: float = 0.6
    tracks: Optional[TrackFilterConfig] = None
    surface: Optional[str] = None
    distance_min: int = 0
    distance_max: int = 9999
    min_expected_value: float = 0.0
    skip_maiden: bool = True
    skip_bad_weather: bool = True
    skip_no_upset: bool = False
```

---

### 2.3 Strategy モジュール

#### 2.3.1 BaseStrategy インターフェース

```python
from typing import Protocol

class StrategyProtocol(Protocol):
    """戦略のプロトコル（インターフェース）"""
    
    @property
    def name(self) -> str:
        """戦略名を返す"""
        ...
    
    @property
    def ticket_type(self) -> str:
        """対象馬券種別を返す"""
        ...
    
    def generate_tickets(self, race: Race) -> List[Ticket]:
        """レースに対して馬券を生成"""
        ...
    
    def should_bet(self, race: Race) -> bool:
        """このレースで賭けるべきか判定"""
        ...
```

#### 2.3.2 StrategyFactory

```python
class StrategyFactory:
    """戦略ファクトリー"""
    
    @classmethod
    def create(cls, name: str, params: Dict[str, Any] = None) -> BaseStrategy:
        """
        戦略名からインスタンスを生成
        
        Args:
            name: 戦略名（'favorite_win', 'box_quinella'等）
            params: 戦略固有のパラメータ
            
        Returns:
            BaseStrategyのサブクラスインスタンス
            
        Raises:
            ValueError: 未知の戦略名
        """
        pass
    
    @classmethod
    def create_composite(
        cls,
        strategies_config: List[Dict[str, Any]]
    ) -> CompositeStrategy:
        """
        複合戦略を生成
        
        Args:
            strategies_config: [{"name": "戦略名", "weight": 重み, "params": {...}}, ...]
            
        Returns:
            CompositeStrategyインスタンス
        """
        pass
    
    @classmethod
    def list_available(cls) -> List[str]:
        """
        利用可能な戦略名のリストを返す
        """
        pass
```

---

### 2.4 FundManager モジュール

#### 2.4.1 BaseFundManager インターフェース

```python
class FundManagerProtocol(Protocol):
    """資金管理のプロトコル"""
    
    def set_fund(self, fund: float) -> None:
        """現在資金を設定"""
        ...
    
    def calculate_bet_amount(self, ticket: Ticket) -> int:
        """賭け金を計算"""
        ...

class FundManagerFactory:
    """資金管理ファクトリー"""
    
    @classmethod
    def create(
        cls,
        method: str,
        params: Dict[str, Any] = None,
        constraints: Dict[str, Any] = None
    ) -> BaseFundManager:
        """
        資金管理方式からインスタンスを生成
        
        Args:
            method: 'fixed', 'percentage', 'kelly'
            params: 方式固有のパラメータ
            constraints: 制約条件
            
        Returns:
            BaseFundManagerのサブクラスインスタンス
        """
        pass
```

#### 2.4.2 制約設定

```python
@dataclass
class FundConstraints:
    """資金管理の制約条件"""
    min_bet: int = 100                    # 最小賭け金
    max_bet_per_ticket: int = 10000       # 1点あたり上限
    max_bet_per_race: int = 30000         # 1レースあたり上限
    max_bet_per_day: int = 100000         # 1日あたり上限
    stop_loss_threshold: float = 0.5      # 損切りライン（初期資金比）
```

---

### 2.5 SimulationEngine モジュール

#### 2.5.1 SimulationEngine クラス

```python
class SimulationEngine:
    """シミュレーション実行エンジン"""
    
    def __init__(
        self,
        strategy: BaseStrategy,
        fund_manager: BaseFundManager,
        evaluator: BetEvaluator,
        race_filter: Optional[RaceFilter] = None
    ):
        """
        Args:
            strategy: 賭け戦略
            fund_manager: 資金管理
            evaluator: 的中判定
            race_filter: レースフィルタ（オプション）
        """
        pass
    
    def run_simple(
        self,
        races: List[Race],
        initial_fund: float
    ) -> SimulationResult:
        """
        単純シミュレーションを実行
        
        Args:
            races: レースデータ
            initial_fund: 初期資金
            
        Returns:
            シミュレーション結果
        """
        pass
    
    def run_monte_carlo(
        self,
        races: List[Race],
        initial_fund: float,
        num_trials: int = 10000,
        method: str = "bootstrap",
        random_seed: int = 42
    ) -> MonteCarloResult:
        """
        モンテカルロシミュレーションを実行
        
        Args:
            races: レースデータ
            initial_fund: 初期資金
            num_trials: 試行回数
            method: 'bootstrap' or 'probability_based'
            random_seed: 乱数シード
            
        Returns:
            モンテカルロ結果
        """
        pass
    
    def run_walk_forward(
        self,
        races: List[Race],
        initial_fund: float,
        train_period_days: int = 180,
        test_period_days: int = 30,
        step_days: int = 30
    ) -> List[SimulationResult]:
        """
        Walk-Forwardシミュレーションを実行
        
        Args:
            races: レースデータ
            initial_fund: 初期資金
            train_period_days: 学習期間（日）
            test_period_days: 検証期間（日）
            step_days: スライド幅（日）
            
        Returns:
            各期間のシミュレーション結果リスト
        """
        pass
```

---

### 2.6 MetricsCalculator モジュール

```python
class MetricsCalculator:
    """評価指標計算"""
    
    def calculate_all(
        self,
        fund_history: List[float],
        bet_history: List[BetRecord],
        initial_fund: float
    ) -> SimulationMetrics:
        """
        全評価指標を計算
        
        Args:
            fund_history: 資金推移
            bet_history: 購入履歴
            initial_fund: 初期資金
            
        Returns:
            評価指標オブジェクト
        """
        pass
    
    # 個別指標計算メソッド
    def calculate_roi(self, total_invested: float, total_payout: float) -> float: ...
    def calculate_cagr(self, initial: float, final: float, years: float) -> float: ...
    def calculate_max_drawdown(self, fund_history: List[float]) -> Tuple[float, int]: ...
    def calculate_sharpe_ratio(self, returns: List[float], risk_free: float = 0) -> float: ...
    def calculate_sortino_ratio(self, returns: List[float], risk_free: float = 0) -> float: ...
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float: ...
    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float: ...
    def calculate_hit_rate(self, bet_history: List[BetRecord]) -> float: ...
    def calculate_max_consecutive_losses(self, bet_history: List[BetRecord]) -> int: ...
```

---

### 2.7 BetEvaluator モジュール

```python
class BetEvaluator:
    """馬券の的中判定と払戻計算"""
    
    def evaluate(self, ticket: Ticket, race: Race) -> Tuple[bool, int]:
        """
        馬券の的中判定と払戻金計算
        
        Args:
            ticket: 馬券データ
            race: レースデータ（結果含む）
            
        Returns:
            (的中フラグ, 払戻金)
        """
        pass
    
    def is_hit(self, ticket: Ticket, race: Race) -> bool:
        """
        的中判定のみ
        """
        pass
    
    def calculate_payout(self, ticket: Ticket, race: Race) -> int:
        """
        払戻金計算（的中前提）
        """
        pass
```

---

### 2.8 Output モジュール

#### 2.8.1 ReportGenerator

```python
class ReportGenerator:
    """レポート生成"""
    
    def __init__(self, output_dir: Union[str, Path]):
        """
        Args:
            output_dir: 出力先ディレクトリ
        """
        pass
    
    def generate_json(
        self,
        result: SimulationResult,
        filename: str = "simulation_result.json"
    ) -> Path:
        """JSON形式でレポート出力"""
        pass
    
    def generate_csv_fund_history(
        self,
        result: SimulationResult,
        filename: str = "fund_history.csv"
    ) -> Path:
        """資金推移CSV出力"""
        pass
    
    def generate_csv_bet_history(
        self,
        result: SimulationResult,
        filename: str = "bet_history.csv"
    ) -> Path:
        """購入履歴CSV出力"""
        pass
    
    def generate_summary_text(
        self,
        result: SimulationResult,
        filename: str = "simulation_summary.txt"
    ) -> Path:
        """サマリーテキスト出力"""
        pass
    
    def generate_all(self, result: SimulationResult) -> Dict[str, Path]:
        """全フォーマットで出力"""
        pass
```

#### 2.8.2 ChartGenerator

```python
class ChartGenerator:
    """グラフ生成"""
    
    def __init__(
        self,
        output_dir: Union[str, Path],
        format: str = "png",
        dpi: int = 150
    ):
        """
        Args:
            output_dir: 出力先ディレクトリ
            format: 'png', 'html', 'both'
            dpi: PNG解像度
        """
        pass
    
    # === 資金推移系 ===
    def plot_fund_history(
        self,
        result: SimulationResult,
        filename: str = "fund_history"
    ) -> Path:
        """資金推移グラフ"""
        pass
    
    def plot_fund_history_multiple(
        self,
        results: List[SimulationResult],
        labels: List[str],
        filename: str = "fund_history_comparison"
    ) -> Path:
        """複数シナリオの資金推移比較"""
        pass
    
    def plot_fund_history_confidence_interval(
        self,
        mc_result: MonteCarloResult,
        filename: str = "fund_history_ci"
    ) -> Path:
        """信頼区間付き資金推移"""
        pass
    
    # === リスク分析系 ===
    def plot_drawdown(
        self,
        result: SimulationResult,
        filename: str = "drawdown"
    ) -> Path:
        """ドローダウン推移"""
        pass
    
    def plot_drawdown_distribution(
        self,
        mc_result: MonteCarloResult,
        filename: str = "drawdown_distribution"
    ) -> Path:
        """最大ドローダウン分布"""
        pass
    
    # === 収益分析系 ===
    def plot_final_fund_distribution(
        self,
        mc_result: MonteCarloResult,
        filename: str = "final_fund_distribution"
    ) -> Path:
        """最終資金分布ヒストグラム"""
        pass
    
    def plot_roi_distribution(
        self,
        mc_result: MonteCarloResult,
        filename: str = "roi_distribution"
    ) -> Path:
        """ROI分布"""
        pass
    
    def plot_monthly_returns(
        self,
        result: SimulationResult,
        filename: str = "monthly_returns"
    ) -> Path:
        """月次リターンバーチャート"""
        pass
    
    # === 的中分析系 ===
    def plot_hit_rate_trend(
        self,
        result: SimulationResult,
        filename: str = "hit_rate_trend"
    ) -> Path:
        """的中率推移"""
        pass
    
    def plot_consecutive_losses_histogram(
        self,
        result: SimulationResult,
        filename: str = "consecutive_losses"
    ) -> Path:
        """連敗ヒストグラム"""
        pass
    
    # === 条件別分析 ===
    def plot_track_roi(
        self,
        result: SimulationResult,
        filename: str = "track_roi"
    ) -> Path:
        """競馬場別ROI"""
        pass
    
    def plot_distance_roi(
        self,
        result: SimulationResult,
        filename: str = "distance_roi"
    ) -> Path:
        """距離別ROI"""
        pass
    
    # === 戦略比較 ===
    def plot_strategy_comparison(
        self,
        results: List[SimulationResult],
        labels: List[str],
        filename: str = "strategy_comparison"
    ) -> Path:
        """戦略別資金推移比較"""
        pass
    
    def plot_risk_return_scatter(
        self,
        results: List[SimulationResult],
        labels: List[str],
        filename: str = "risk_return"
    ) -> Path:
        """リスクリターン散布図"""
        pass
    
    # === 一括生成 ===
    def generate_all(
        self,
        result: SimulationResult,
        mc_result: Optional[MonteCarloResult] = None
    ) -> Dict[str, Path]:
        """全グラフを生成"""
        pass
```

---

## 3. CLI インターフェース

### 3.1 コマンド構造

```
betting-sim [OPTIONS] COMMAND [ARGS]...

Commands:
  run        シミュレーションを実行
  validate   入力ファイルをバリデーション
  compare    複数戦略を比較
  report     既存結果からレポート生成
  list       利用可能な戦略/資金管理方式を一覧
```

### 3.2 run コマンド

```
Usage: betting-sim run [OPTIONS]

  シミュレーションを実行する

Options:
  -c, --config PATH           設定ファイルパス（YAML）
  -i, --input PATH            入力TSVファイルパス（複数指定可）  [required]
  -o, --output PATH           出力ディレクトリ  [default: ./output]
  
  --type [simple|monte_carlo|walk_forward]
                              シミュレーション種別  [default: simple]
  --initial-fund FLOAT        初期資金  [default: 100000]
  --strategy TEXT             戦略名  [default: favorite_win]
  --fund-method [fixed|percentage|kelly]
                              資金管理方式  [default: kelly]
  
  --trials INTEGER            モンテカルロ試行回数  [default: 10000]
  --seed INTEGER              乱数シード  [default: 42]
  
  --charts / --no-charts      グラフ生成  [default: charts]
  --format [png|html|both]    グラフ形式  [default: png]
  
  -v, --verbose               詳細ログ出力
  --help                      ヘルプを表示

Examples:
  # 基本的な実行
  betting-sim run -i predictions.tsv
  
  # 設定ファイルを使用
  betting-sim run -c config/my_config.yaml -i predictions.tsv
  
  # モンテカルロシミュレーション
  betting-sim run -i predictions.tsv --type monte_carlo --trials 5000
  
  # 複数ファイル入力
  betting-sim run -i predictions_2024.tsv -i predictions_2025.tsv
```

### 3.3 validate コマンド

```
Usage: betting-sim validate [OPTIONS] INPUT

  入力TSVファイルをバリデーションする

Options:
  --strict          厳格モード（警告もエラーとして扱う）
  --help            ヘルプを表示

Examples:
  betting-sim validate predictions.tsv
```

### 3.4 compare コマンド

```
Usage: betting-sim compare [OPTIONS]

  複数の戦略を比較シミュレーションする

Options:
  -i, --input PATH            入力TSVファイルパス  [required]
  -o, --output PATH           出力ディレクトリ  [default: ./output/comparison]
  --strategies TEXT           比較する戦略名（カンマ区切り）  [required]
  --initial-fund FLOAT        初期資金  [default: 100000]
  --help                      ヘルプを表示

Examples:
  betting-sim compare -i predictions.tsv --strategies "favorite_win,box_quinella,value_win"
```

### 3.5 list コマンド

```
Usage: betting-sim list [OPTIONS] [TYPE]

  利用可能な戦略や資金管理方式を一覧表示

Arguments:
  TYPE  表示する種類 [strategies|fund_methods|all]  [default: all]

Examples:
  betting-sim list strategies
  betting-sim list fund_methods
```

---

## 4. 設定ファイルスキーマ（YAML）

### 4.1 完全スキーマ

```yaml
# =============================================================================
# 競馬賭けシミュレーション設定ファイル
# =============================================================================

# -----------------------------------------------------------------------------
# シミュレーション基本設定
# -----------------------------------------------------------------------------
simulation:
  # シミュレーション種別: simple | monte_carlo | walk_forward
  type: simple
  
  # 初期資金（円）
  initial_fund: 100000
  
  # 乱数シード（再現性確保、0の場合はランダム）
  random_seed: 42

# -----------------------------------------------------------------------------
# モンテカルロ設定（simulation.type: monte_carlo の場合）
# -----------------------------------------------------------------------------
monte_carlo:
  # 試行回数
  num_trials: 10000
  
  # シミュレーション手法: bootstrap | probability_based
  method: bootstrap
  
  # 信頼水準（信頼区間計算用）
  confidence_level: 0.95

# -----------------------------------------------------------------------------
# Walk-Forward設定（simulation.type: walk_forward の場合）
# -----------------------------------------------------------------------------
walk_forward:
  # 学習期間（日）
  train_period_days: 180
  
  # 検証期間（日）
  test_period_days: 30
  
  # スライド幅（日）
  step_days: 30

# -----------------------------------------------------------------------------
# 戦略設定
# -----------------------------------------------------------------------------
strategy:
  # 戦略名
  # 単勝: favorite_win, longshot_win, value_win
  # 複勝: favorite_place, longshot_place
  # 馬連: favorite_quinella, favorite_longshot_quinella, box_quinella
  # ワイド: favorite_wide, favorite_longshot_wide, box_wide
  # 三連複: favorite_trio, favorite2_longshot_trio, formation_trio
  name: favorite_win
  
  # 戦略固有パラメータ（戦略ごとに異なる）
  params:
    # favorite_win / favorite_place
    top_n: 1
    min_odds: 1.1
    max_odds: 100.0
    
    # longshot_win / longshot_place
    upset_threshold: 0.5
    max_candidates: 2
    
    # value_win
    min_expected_value: 1.2
    max_tickets: 3
    
    # box_quinella / box_wide
    box_size: 4
    
    # favorite_longshot_quinella / favorite2_longshot_trio
    max_counterparts: 3
    
    # formation_trio
    first_leg: [1, 2]
    second_leg: [1, 2, 3]
    third_leg: [1, 2, 3, 4, 5]

# -----------------------------------------------------------------------------
# 複合戦略設定（複数戦略を組み合わせる場合）
# -----------------------------------------------------------------------------
composite_strategy:
  # 複合戦略を使用するか
  enabled: false
  
  # 戦略リスト
  strategies:
    - name: favorite_win
      weight: 0.5
      params:
        top_n: 1
    - name: longshot_place
      weight: 0.3
      params:
        upset_threshold: 0.6
    - name: box_quinella
      weight: 0.2
      params:
        box_size: 3

# -----------------------------------------------------------------------------
# 資金管理設定
# -----------------------------------------------------------------------------
fund_management:
  # 資金管理方式: fixed | percentage | kelly
  method: kelly
  
  # 方式固有パラメータ
  params:
    # fixed: 1点あたり固定賭け金
    bet_amount: 1000
    
    # percentage: 資金に対する比率（0.0-1.0）
    bet_percentage: 0.02
    
    # kelly: ケリー基準のフラクション（0.0-1.0）
    kelly_fraction: 0.25
  
  # 制約条件
  constraints:
    # 最小賭け金（これ未満は見送り）
    min_bet: 100
    
    # 1点あたり上限
    max_bet_per_ticket: 5000
    
    # 1レースあたり上限
    max_bet_per_race: 15000
    
    # 1日あたり上限
    max_bet_per_day: 50000
    
    # 損切りライン（初期資金に対する比率、これを下回ったら停止）
    stop_loss_threshold: 0.5

# -----------------------------------------------------------------------------
# レースフィルタ設定
# -----------------------------------------------------------------------------
race_filter:
  # 基本フィルタ
  min_horse_count: 12
  min_confidence: 0.6
  
  # 競馬場フィルタ
  tracks:
    # モード: whitelist | blacklist | tier
    mode: tier
    
    # whitelist/blacklistの場合のリスト
    list: []
    
    # tierモードの場合の設定（tierが低いほど優先）
    tiers:
      tier1: [東京, 中山, 阪神, 京都]  # 賭け金100%
      tier2: [中京, 新潟]              # 賭け金80%
      tier3: [小倉, 福島, 札幌, 函館]   # 賭け金60%
  
  # コース種別フィルタ（null=両方, "芝", "ダート"）
  surface: null
  
  # 距離フィルタ
  distance:
    min: 1200
    max: 3600
  
  # 期待値フィルタ
  min_expected_value: 1.0
  
  # 見送り条件
  skip_conditions:
    # 新馬戦・未勝利戦を見送り
    maiden_race: true
    
    # 荒天時を見送り
    bad_weather: true
    
    # 穴馬候補がいないレースを見送り
    no_upset_candidate: false

# -----------------------------------------------------------------------------
# 出力設定
# -----------------------------------------------------------------------------
output:
  # 出力ディレクトリ
  directory: ./output
  
  # 出力フォーマット
  formats:
    json: true
    csv: true
    txt: true
  
  # グラフ設定
  charts:
    enabled: true
    format: png    # png | html | both
    dpi: 150
    
    # 生成するグラフの選択（trueで生成）
    types:
      fund_history: true
      drawdown: true
      final_fund_distribution: true
      roi_distribution: true
      hit_rate_trend: true
      track_roi: true
      monthly_returns: true

# -----------------------------------------------------------------------------
# ロギング設定
# -----------------------------------------------------------------------------
logging:
  # ログレベル: DEBUG | INFO | WARNING | ERROR
  level: INFO
  
  # ログファイルパス（nullでファイル出力なし）
  file: ./logs/simulation.log
  
  # コンソール出力
  console: true
```

### 4.2 最小設定例

```yaml
# 最小限の設定
simulation:
  initial_fund: 100000

strategy:
  name: favorite_win

fund_management:
  method: kelly
```

### 4.3 モンテカルロ設定例

```yaml
simulation:
  type: monte_carlo
  initial_fund: 100000
  random_seed: 42

monte_carlo:
  num_trials: 10000
  method: bootstrap

strategy:
  name: box_quinella
  params:
    box_size: 4

fund_management:
  method: kelly
  params:
    kelly_fraction: 0.25
```

---

## 5. エラーコード一覧

| コード | 名前 | 説明 |
|--------|------|------|
| E001 | FILE_NOT_FOUND | 入力ファイルが見つからない |
| E002 | INVALID_FORMAT | ファイルフォーマットが不正 |
| E003 | MISSING_COLUMN | 必須カラムが欠損 |
| E004 | INVALID_VALUE | 値が不正（範囲外等） |
| E010 | CONFIG_NOT_FOUND | 設定ファイルが見つからない |
| E011 | INVALID_CONFIG | 設定値が不正 |
| E012 | MISSING_CONFIG | 必須設定が欠損 |
| E020 | UNKNOWN_STRATEGY | 未知の戦略名 |
| E021 | INVALID_STRATEGY_PARAM | 戦略パラメータが不正 |
| E030 | UNKNOWN_FUND_METHOD | 未知の資金管理方式 |
| E031 | INVALID_FUND_PARAM | 資金管理パラメータが不正 |
| E040 | SIMULATION_ERROR | シミュレーション実行エラー |
| E041 | INSUFFICIENT_FUND | 資金不足 |
| E050 | OUTPUT_ERROR | 出力エラー |
| E051 | CHART_GENERATION_ERROR | グラフ生成エラー |

---

## 6. イベント・コールバック

### 6.1 進捗通知

```python
from typing import Callable, Optional

class SimulationEngine:
    def set_progress_callback(
        self,
        callback: Callable[[int, int, str], None]
    ) -> None:
        """
        進捗コールバックを設定
        
        Args:
            callback: コールバック関数
                      引数: (current, total, message)
        """
        pass

# 使用例
def on_progress(current: int, total: int, message: str):
    percent = current / total * 100
    print(f"\r[{percent:5.1f}%] {message}", end="")

engine.set_progress_callback(on_progress)
```

### 6.2 イベントフック

```python
class SimulationEngine:
    def on_race_start(self, callback: Callable[[Race], None]) -> None:
        """レース処理開始時のフック"""
        pass
    
    def on_bet_placed(self, callback: Callable[[Ticket, Race], None]) -> None:
        """馬券購入時のフック"""
        pass
    
    def on_race_result(self, callback: Callable[[BetRecord], None]) -> None:
        """レース結果確定時のフック"""
        pass
    
    def on_bankruptcy(self, callback: Callable[[float], None]) -> None:
        """破産時のフック"""
        pass
```

---

## 7. 型定義

### 7.1 TypedDict定義

```python
from typing import TypedDict, List, Optional

class StrategyConfig(TypedDict):
    name: str
    params: dict

class FundManagementConfig(TypedDict):
    method: str
    params: dict
    constraints: dict

class SimulationConfig(TypedDict):
    type: str
    initial_fund: float
    random_seed: int
    strategy: StrategyConfig
    fund_management: FundManagementConfig

class ValidationError(TypedDict):
    line: int
    column: str
    message: str
    severity: str  # 'error' | 'warning'

class ValidationResult(TypedDict):
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
```

---

**文書情報**
- 作成日: 2026-01-21
- バージョン: 1.0.0
- 関連文書: [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md), [DATA_DESIGN.md](./DATA_DESIGN.md)
