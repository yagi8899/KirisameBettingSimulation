# 競馬賭けシミュレーションシステム

過去の競馬予測データを用いて、様々な賭け戦略をシミュレーションするシステム。

## インストール

> ⚠️ **重要**: 必ずvenv仮想環境内でインストールしてください

```bash
# 仮想環境の作成と有効化
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# パッケージのインストール
pip install -e ".[dev]"
```

## 使い方

```bash
# シミュレーション実行
betting-sim run config.yaml

# 戦略一覧表示
betting-sim list-strategies

# 設定ファイル検証
betting-sim validate config.yaml
```

## 開発

```bash
# テスト実行
pytest

# カバレッジ付き
pytest --cov=src --cov-report=html

# 型チェック
mypy src

# リント
ruff check src
```

## ドキュメント

- [要件定義書](docs/REQUIREMENTS_BETTING_SIMULATOR.md)
- [技術設計書](docs/TECHNICAL_DESIGN.md)
- [データ設計書](docs/DATA_DESIGN.md)
- [戦略・アルゴリズム設計書](docs/STRATEGY_ALGORITHM.md)
- [API・インターフェース設計書](docs/API_INTERFACE.md)
- [UI/UX設計書](docs/UI_UX_DESIGN.md)
- [テスト計画書](docs/TEST_PLAN.md)
- [開発ロードマップ](docs/DEVELOPMENT_ROADMAP.md)

## ライセンス

MIT
