# 技術設計書（Technical Design Document）

## 1. 概要

本ドキュメントは、競馬賭けシミュレーションシステムの技術的なアーキテクチャ、ディレクトリ構成、モジュール分割、および技術スタックを定義する。

### 1.1 システム名
**Kirisame Betting Simulation System（霧雨賭けシミュレーションシステム）**

### 1.2 対象読者
- 開発者
- システム設計者
- 保守担当者

---

## 2. 技術スタック

### 2.1 言語・ランタイム

| 項目 | 技術 | バージョン | 備考 |
|------|------|-----------|------|
| 言語 | Python | 3.10+ | 型ヒント、dataclass活用 |
| パッケージ管理 | pip / pyproject.toml | - | PEP 517/518準拠 |

### 2.2 主要ライブラリ

| カテゴリ | ライブラリ | バージョン | 用途 |
|----------|-----------|-----------|------|
| データ処理 | pandas | >=2.0.0 | TSV読み込み、データ集約 |
| 数値計算 | numpy | >=1.24.0 | 統計計算、乱数生成 |
| 可視化（静的） | matplotlib | >=3.7.0 | PNG出力グラフ |
| 可視化（動的） | plotly | >=5.15.0 | インタラクティブHTML |
| ダッシュボード | streamlit | >=1.28.0 | WebUI（Phase 3） |
| 設定管理 | pyyaml | >=6.0 | YAML設定ファイル |
| 進捗表示 | tqdm | >=4.65.0 | シミュレーション進捗 |
| CLI | click | >=8.1.0 | コマンドライン引数 |
| テスト | pytest | >=7.4.0 | 単体テスト |
| 型チェック | mypy | >=1.5.0 | 静的型解析 |
| コード品質 | ruff | >=0.1.0 | Linter/Formatter |

### 2.3 開発環境

| 項目 | 推奨ツール |
|------|-----------|
| IDE | VS Code + Python拡張 |
| 仮想環境 | venv または conda |
| バージョン管理 | Git |
| ノートブック | Jupyter Notebook / JupyterLab |

---

## 3. システムアーキテクチャ

### 3.1 アーキテクチャ概要図

```
┌─────────────────────────────────────────────────────────────────┐
│                        入力層（Input Layer）                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  予測結果TSV    │  │  設定YAML       │  │  CLI引数        │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
└───────────┼────────────────────┼────────────────────┼───────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      コア層（Core Layer）                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Data Loader                               ││
│  │         （TSV読込 → Race/Horseオブジェクト変換）              ││
│  └─────────────────────────┬───────────────────────────────────┘│
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  Race Filter Engine                          ││
│  │           （レース選択・フィルタリング処理）                   ││
│  └─────────────────────────┬───────────────────────────────────┘│
│                            ▼                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Strategy     │  │ Fund         │  │ Bet          │          │
│  │ Engine       │◄─┤ Manager      │◄─┤ Evaluator    │          │
│  │ （賭け戦略）  │  │ （資金管理）  │  │ （的中判定）  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                 Simulation Engine                            ││
│  │    （単純/モンテカルロ/Walk-Forward シミュレーション）        ││
│  └─────────────────────────┬───────────────────────────────────┘│
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Metrics Calculator                         ││
│  │         （ROI/ドローダウン/破産確率等の計算）                 ││
│  └─────────────────────────┬───────────────────────────────────┘│
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      出力層（Output Layer）                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Report       │  │ Chart        │  │ Dashboard    │          │
│  │ Generator    │  │ Generator    │  │ (Streamlit)  │          │
│  │ （JSON/CSV） │  │ （PNG/HTML） │  │ （WebUI）    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 レイヤー責務

| レイヤー | 責務 | 主要コンポーネント |
|----------|------|-------------------|
| Input Layer | 外部データの受け取り | TSVパーサー、YAML設定ローダー、CLIパーサー |
| Core Layer | ビジネスロジック | シミュレーション、戦略、資金管理、評価 |
| Output Layer | 結果の出力 | レポート生成、グラフ生成、ダッシュボード |

---

## 4. ディレクトリ構成

```
KirisameBettingSimulation/
├── pyproject.toml              # プロジェクト設定・依存関係
├── README.md                   # プロジェクト説明
├── .gitignore                  # Git除外設定
│
├── docs/                       # ドキュメント
│   ├── REQUIREMENTS_BETTING_SIMULATOR.md  # 要件定義書
│   ├── TECHNICAL_DESIGN.md     # 技術設計書（本書）
│   ├── DATA_DESIGN.md          # データ設計書
│   ├── STRATEGY_ALGORITHM.md   # 戦略・アルゴリズム設計書
│   ├── API_INTERFACE.md        # API・インターフェース設計書
│   ├── UI_UX_DESIGN.md         # UI/UX設計書
│   └── TEST_PLAN.md            # テスト計画書
│
├── config/                     # 設定ファイル
│   ├── default_config.yaml     # デフォルト設定
│   └── example_config.yaml     # サンプル設定
│
├── src/                        # ソースコード
│   └── betting_simulation/     # メインパッケージ
│       ├── __init__.py
│       ├── __main__.py         # CLIエントリーポイント
│       │
│       ├── core/               # コアモジュール
│       │   ├── __init__.py
│       │   ├── data_loader.py      # データ読み込み
│       │   ├── race_filter.py      # レースフィルタ
│       │   ├── simulation_engine.py # シミュレーションエンジン
│       │   └── metrics_calculator.py # 評価指標計算
│       │
│       ├── strategy/           # 戦略モジュール
│       │   ├── __init__.py
│       │   ├── base_strategy.py    # 戦略基底クラス
│       │   ├── win_strategy.py     # 単勝戦略
│       │   ├── place_strategy.py   # 複勝戦略
│       │   ├── quinella_strategy.py # 馬連戦略
│       │   ├── wide_strategy.py    # ワイド戦略
│       │   ├── trio_strategy.py    # 三連複戦略
│       │   └── composite_strategy.py # 複合戦略
│       │
│       ├── fund/               # 資金管理モジュール
│       │   ├── __init__.py
│       │   ├── base_fund_manager.py # 資金管理基底クラス
│       │   ├── fixed_manager.py     # 固定賭け金方式
│       │   ├── percentage_manager.py # 資金比率方式
│       │   └── kelly_manager.py     # ケリー基準方式
│       │
│       ├── evaluator/          # 評価モジュール
│       │   ├── __init__.py
│       │   ├── bet_evaluator.py     # 的中判定・払戻計算
│       │   ├── expected_value.py    # 期待値計算
│       │   └── race_confidence.py   # レース信頼度スコア
│       │
│       ├── models/             # データモデル
│       │   ├── __init__.py
│       │   ├── horse.py            # 馬データクラス
│       │   ├── race.py             # レースデータクラス
│       │   ├── ticket.py           # 馬券データクラス
│       │   └── simulation_result.py # シミュレーション結果
│       │
│       ├── output/             # 出力モジュール
│       │   ├── __init__.py
│       │   ├── report_generator.py # レポート生成
│       │   └── chart_generator.py  # グラフ生成
│       │
│       └── utils/              # ユーティリティ
│           ├── __init__.py
│           ├── config_loader.py    # 設定ファイル読み込み
│           └── logger.py           # ロギング設定
│
├── notebooks/                  # Jupyterノートブック
│   ├── 01_basic_simulation.ipynb
│   ├── 02_strategy_comparison.ipynb
│   ├── 03_monte_carlo_analysis.ipynb
│   ├── 04_walk_forward_analysis.ipynb
│   ├── 05_risk_analysis.ipynb
│   └── 06_parameter_tuning.ipynb
│
├── dashboard/                  # Streamlitダッシュボード
│   ├── app.py                  # メインアプリ
│   ├── pages/                  # 各ページ
│   │   ├── 01_summary.py
│   │   ├── 02_fund_history.py
│   │   ├── 03_risk_analysis.py
│   │   ├── 04_hit_analysis.py
│   │   ├── 05_condition_analysis.py
│   │   ├── 06_strategy_comparison.py
│   │   ├── 07_monte_carlo.py
│   │   └── 08_settings.py
│   └── components/             # 共通コンポーネント
│       ├── charts.py
│       └── widgets.py
│
├── tests/                      # テストコード
│   ├── __init__.py
│   ├── conftest.py             # pytest設定・fixture
│   ├── test_data/              # テスト用データ
│   │   └── sample_predictions.tsv
│   ├── unit/                   # 単体テスト
│   │   ├── test_data_loader.py
│   │   ├── test_strategies.py
│   │   ├── test_fund_managers.py
│   │   ├── test_bet_evaluator.py
│   │   └── test_metrics.py
│   └── integration/            # 結合テスト
│       └── test_simulation_flow.py
│
├── data/                       # データディレクトリ
│   ├── input/                  # 入力データ（予測結果TSV）
│   └── output/                 # 出力データ
│       ├── results/            # シミュレーション結果
│       └── charts/             # 生成グラフ
│
└── scripts/                    # ユーティリティスクリプト
    ├── run_simulation.py       # シミュレーション実行
    └── generate_report.py      # レポート生成
```

---

## 5. モジュール設計

### 5.1 モジュール依存関係図

```
                    ┌─────────────┐
                    │   __main__  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │   config    │ │    core     │ │   output    │
    │   loader    │ │             │ │             │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           │       ┌───────┴───────┐       │
           │       ▼               ▼       │
           │ ┌───────────┐ ┌───────────┐   │
           │ │ strategy  │ │   fund    │   │
           │ └─────┬─────┘ └─────┬─────┘   │
           │       │             │         │
           │       └──────┬──────┘         │
           │              ▼                │
           │       ┌───────────┐           │
           │       │ evaluator │           │
           │       └─────┬─────┘           │
           │             │                 │
           └─────────────┼─────────────────┘
                         ▼
                  ┌─────────────┐
                  │   models    │
                  └─────────────┘
```

### 5.2 主要モジュール責務

| モジュール | ファイル | 責務 |
|-----------|---------|------|
| **core** | data_loader.py | TSVファイル読込、Race/Horseオブジェクト生成 |
| | race_filter.py | レース選択条件によるフィルタリング |
| | simulation_engine.py | 単純/MC/WFシミュレーション実行 |
| | metrics_calculator.py | 収益/リスク/的中指標の計算 |
| **strategy** | base_strategy.py | 戦略の抽象基底クラス定義 |
| | *_strategy.py | 各馬券種別の戦略実装 |
| **fund** | base_fund_manager.py | 資金管理の抽象基底クラス |
| | *_manager.py | 各資金管理方式の実装 |
| **evaluator** | bet_evaluator.py | 馬券の的中判定と払戻金計算 |
| | expected_value.py | 期待値計算ロジック |
| | race_confidence.py | レース信頼度スコア計算 |
| **models** | *.py | データクラス（Horse, Race, Ticket等） |
| **output** | report_generator.py | JSON/CSV/TXTレポート生成 |
| | chart_generator.py | matplotlib/plotlyグラフ生成 |
| **utils** | config_loader.py | YAML設定ファイル読込・バリデーション |
| | logger.py | ログ出力設定 |

---

## 6. クラス設計

### 6.1 コアクラス階層

```
                         ┌──────────────────┐
                         │   ABC (Protocol) │
                         └────────┬─────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────┐
│ BaseStrategy  │        │BaseFundManager│        │   Evaluator   │
│   (Protocol)  │        │   (Protocol)  │        │   Protocol    │
└───────┬───────┘        └───────┬───────┘        └───────────────┘
        │                        │
   ┌────┴────┬────┬────┐    ┌────┴────┬────┐
   ▼         ▼    ▼    ▼    ▼         ▼    ▼
┌──────┐ ┌──────┐...   ┌──────┐ ┌──────┐ ┌──────┐
│ Win  │ │Place │      │Fixed │ │ %    │ │Kelly │
│Strat.│ │Strat.│      │Mgr.  │ │Mgr.  │ │Mgr.  │
└──────┘ └──────┘      └──────┘ └──────┘ └──────┘
```

### 6.2 主要クラス一覧

| クラス名 | モジュール | 責務 |
|----------|-----------|------|
| `Horse` | models/horse.py | 馬データの保持 |
| `Race` | models/race.py | レースデータの保持 |
| `Ticket` | models/ticket.py | 馬券データの保持 |
| `SimulationResult` | models/simulation_result.py | シミュレーション結果保持 |
| `DataLoader` | core/data_loader.py | TSVファイル読込・パース |
| `RaceFilter` | core/race_filter.py | レース選択フィルタ |
| `SimulationEngine` | core/simulation_engine.py | シミュレーション実行制御 |
| `MetricsCalculator` | core/metrics_calculator.py | 評価指標計算 |
| `BaseStrategy` | strategy/base_strategy.py | 戦略基底クラス |
| `BaseFundManager` | fund/base_fund_manager.py | 資金管理基底クラス |
| `BetEvaluator` | evaluator/bet_evaluator.py | 的中判定・払戻計算 |
| `ConfigLoader` | utils/config_loader.py | 設定ファイル読込 |
| `ReportGenerator` | output/report_generator.py | レポート生成 |
| `ChartGenerator` | output/chart_generator.py | グラフ生成 |

---

## 7. 設計原則

### 7.1 SOLID原則の適用

| 原則 | 適用箇所 |
|------|---------|
| **S**ingle Responsibility | 各モジュール・クラスは単一の責務のみを持つ |
| **O**pen/Closed | 新戦略はBaseStrategyを継承して追加（既存コード修正不要） |
| **L**iskov Substitution | 全ての戦略クラスはBaseStrategyと置換可能 |
| **I**nterface Segregation | 必要なインターフェースのみを定義 |
| **D**ependency Inversion | 上位モジュールは抽象（Protocol）に依存 |

### 7.2 デザインパターン

| パターン | 適用箇所 | 目的 |
|----------|---------|------|
| Strategy | 賭け戦略、資金管理 | アルゴリズムの切り替え |
| Factory | 戦略・資金管理クラス生成 | オブジェクト生成の隠蔽 |
| Template Method | シミュレーションエンジン | 処理フローの共通化 |
| Builder | SimulationConfigビルダー | 複雑な設定オブジェクト構築 |
| Observer | 進捗通知 | シミュレーション進捗の通知 |

---

## 8. エラーハンドリング

### 8.1 例外階層

```python
BettingSimulationError (基底例外)
├── DataLoadError          # データ読み込みエラー
│   ├── FileNotFoundError  # ファイルが見つからない
│   └── InvalidFormatError # フォーマット不正
├── ConfigurationError     # 設定エラー
│   ├── InvalidConfigError # 設定値不正
│   └── MissingConfigError # 必須設定欠損
├── SimulationError        # シミュレーションエラー
│   ├── InsufficientFundError  # 資金不足
│   └── InvalidStrategyError   # 戦略設定不正
└── OutputError            # 出力エラー
    ├── ChartGenerationError   # グラフ生成失敗
    └── ReportGenerationError  # レポート生成失敗
```

### 8.2 エラーハンドリング方針

1. **早期リターン**: 無効な入力は早期に検出して例外をスロー
2. **詳細メッセージ**: エラー原因と解決策を含むメッセージを提供
3. **ロギング**: 全ての例外をログに記録
4. **グレースフルデグラデーション**: 可能な限り処理を継続

---

## 9. ロギング設計

### 9.1 ログレベル

| レベル | 用途 |
|--------|------|
| DEBUG | 詳細なデバッグ情報 |
| INFO | 正常な処理の進捗 |
| WARNING | 潜在的な問題（処理は継続） |
| ERROR | エラー発生（一部機能停止） |
| CRITICAL | 致命的エラー（システム停止） |

### 9.2 ログ出力先

| 出力先 | 用途 |
|--------|------|
| コンソール | INFO以上をリアルタイム表示 |
| ファイル | DEBUG以上を永続化 |
| 構造化ログ | JSON形式で分析用 |

---

## 10. パフォーマンス考慮

### 10.1 最適化ポイント

| 項目 | 対策 |
|------|------|
| TSV読み込み | pandas.read_csv()のchunksize活用 |
| モンテカルロ | numpy vectorization、並列処理（multiprocessing） |
| メモリ使用 | ジェネレータ活用、不要データの早期解放 |
| グラフ生成 | バッチ処理、キャッシュ活用 |

### 10.2 パフォーマンス目標

| 処理 | 目標時間 |
|------|---------|
| TSV読み込み（10万行） | < 5秒 |
| 単純シミュレーション（1年分） | < 1秒 |
| モンテカルロ（10,000試行） | < 60秒 |
| グラフ生成（全39種） | < 30秒 |

---

## 11. セキュリティ考慮

### 11.1 対象リスク

| リスク | 対策 |
|--------|------|
| パストラバーサル | 入力ファイルパスの検証 |
| YAML安全性 | yaml.safe_load()の使用 |
| 設定ファイル改竄 | スキーマバリデーション |

---

## 12. 開発フロー

### 12.1 ブランチ戦略

```
main ─────────────────────────────────────────────►
       │                    │
       └─ develop ──────────┴─────────────────────►
              │       │       │
              └─ feature/xxx ─┘
              └─ feature/yyy ─┘
```

### 12.2 コード品質基準

| 項目 | 基準 |
|------|------|
| テストカバレッジ | 80%以上 |
| 型ヒント | 100%付与 |
| docstring | 全public関数・クラスに必須 |
| Lintエラー | 0件 |

---

## 13. 既存コンポーネント流用

要件定義で示された以下のコンポーネントを流用・参考にする：

| コンポーネント | 流用方針 |
|---------------|---------|
| bet_evaluator.py | 的中判定・払戻計算ロジックを移植 |
| kelly_criterion.py | ケリー基準計算を資金管理モジュールに統合 |
| expected_value_calculator.py | 期待値計算をevaluatorモジュールに統合 |
| race_confidence_scorer.py | レース信頼度スコア計算を移植 |

---

## 14. 付録

### 14.1 用語集

| 用語 | 説明 |
|------|------|
| ROI | Return on Investment（投資収益率） |
| ドローダウン | 最高資金からの下落率 |
| ケリー基準 | 最適賭け金を算出する数学的手法 |
| モンテカルロ | 乱数を用いた統計的シミュレーション手法 |
| Walk-Forward | 学習・検証期間をスライドさせる分析手法 |

### 14.2 参考資料

- 要件定義書: [REQUIREMENTS_BETTING_SIMULATOR.md](./REQUIREMENTS_BETTING_SIMULATOR.md)
- データ設計書: [DATA_DESIGN.md](./DATA_DESIGN.md)
- 戦略アルゴリズム設計書: [STRATEGY_ALGORITHM.md](./STRATEGY_ALGORITHM.md)

---

**文書情報**
- 作成日: 2026-01-21
- バージョン: 1.0.0
- 作成者: Development Team
