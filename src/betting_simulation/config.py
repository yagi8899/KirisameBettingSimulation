"""設定ファイル読み込み

YAML設定ファイルの読み込みとバリデーション。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from betting_simulation.fund_manager import FundConstraints
from betting_simulation.race_filter import FilterCondition


@dataclass
class SimulationConfig:
    """シミュレーション設定"""
    # 基本設定
    initial_fund: int = 100000
    
    # データソース
    data_path: str = ""
    
    # フィルター条件
    filter_condition: FilterCondition = field(default_factory=FilterCondition)
    
    # 戦略設定
    strategy_name: str = "favorite_win"
    strategy_params: dict[str, Any] = field(default_factory=dict)
    
    # 資金管理設定
    fund_manager_name: str = "fixed"
    fund_manager_params: dict[str, Any] = field(default_factory=dict)
    fund_constraints: FundConstraints = field(default_factory=FundConstraints)
    
    # モンテカルロ設定
    monte_carlo_trials: int = 10000
    random_seed: int | None = None
    
    # 出力設定
    output_dir: str = "output"
    output_format: list[str] = field(default_factory=lambda: ["json"])
    
    @classmethod
    def from_dict(cls, data: dict) -> "SimulationConfig":
        """辞書から設定を作成"""
        config = cls()
        
        # 基本設定
        config.initial_fund = data.get("initial_fund", 100000)
        config.data_path = data.get("data_path", "")
        
        # フィルター条件
        if "filter" in data:
            config.filter_condition = FilterCondition.from_dict(data["filter"])
        
        # 戦略設定（2つの形式をサポート）
        # 形式1: strategy_name / strategy_params（フラット形式）
        # 形式2: strategy.name / strategy.params（ネスト形式）
        if "strategy" in data:
            strategy = data["strategy"]
            config.strategy_name = strategy.get("name", "favorite_win")
            config.strategy_params = strategy.get("params", {})
        elif "strategy_name" in data:
            config.strategy_name = data.get("strategy_name", "favorite_win")
            config.strategy_params = data.get("strategy_params", {})
        
        # 資金管理設定（2つの形式をサポート）
        if "fund_manager" in data:
            fm = data["fund_manager"]
            config.fund_manager_name = fm.get("name", "fixed")
            config.fund_manager_params = fm.get("params", {})
            if "constraints" in fm:
                config.fund_constraints = FundConstraints.from_dict(fm["constraints"])
        elif "fund_manager_name" in data:
            config.fund_manager_name = data.get("fund_manager_name", "fixed")
            config.fund_manager_params = data.get("fund_manager_params", {})
        
        # モンテカルロ設定
        if "monte_carlo" in data:
            mc = data["monte_carlo"]
            config.monte_carlo_trials = mc.get("trials", 10000)
            config.random_seed = mc.get("random_seed")
        
        # 出力設定
        if "output" in data:
            out = data["output"]
            config.output_dir = out.get("dir", "output")
            config.output_format = out.get("format", ["json"])
        
        return config
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "initial_fund": self.initial_fund,
            "data_path": self.data_path,
            "filter": {
                "tracks": self.filter_condition.tracks,
                "surfaces": [s.value for s in self.filter_condition.surfaces],
                "min_distance": self.filter_condition.min_distance,
                "max_distance": self.filter_condition.max_distance,
                "years": self.filter_condition.years,
                "race_numbers": self.filter_condition.race_numbers,
                "min_horses": self.filter_condition.min_horses,
                "max_horses": self.filter_condition.max_horses,
            },
            "strategy": {
                "name": self.strategy_name,
                "params": self.strategy_params,
            },
            "fund_manager": {
                "name": self.fund_manager_name,
                "params": self.fund_manager_params,
                "constraints": {
                    "min_bet": self.fund_constraints.min_bet,
                    "max_bet_per_ticket": self.fund_constraints.max_bet_per_ticket,
                    "max_bet_per_race": self.fund_constraints.max_bet_per_race,
                    "max_bet_ratio": self.fund_constraints.max_bet_ratio,
                    "bet_unit": self.fund_constraints.bet_unit,
                },
            },
            "monte_carlo": {
                "trials": self.monte_carlo_trials,
                "random_seed": self.random_seed,
            },
            "output": {
                "dir": self.output_dir,
                "format": self.output_format,
            },
        }


class ConfigLoader:
    """設定ファイルローダー"""
    
    @staticmethod
    def load(file_path: str | Path) -> SimulationConfig:
        """YAMLファイルから設定を読み込む
        
        Args:
            file_path: YAMLファイルパス
            
        Returns:
            SimulationConfig
            
        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: 設定が不正な場合
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if data is None:
            raise ValueError("Empty config file")
        
        return SimulationConfig.from_dict(data)
    
    @staticmethod
    def validate(config: SimulationConfig) -> list[str]:
        """設定のバリデーション
        
        Returns:
            エラーメッセージのリスト（空なら有効）
        """
        errors = []
        
        # 初期資金チェック
        if config.initial_fund <= 0:
            errors.append("initial_fund must be positive")
        
        # データパスチェック
        if config.data_path and not Path(config.data_path).exists():
            errors.append(f"data_path does not exist: {config.data_path}")
        
        # 戦略チェック
        from betting_simulation.strategy import StrategyFactory
        try:
            StrategyFactory.create(config.strategy_name, config.strategy_params)
        except ValueError as e:
            errors.append(str(e))
        
        # 資金管理チェック
        from betting_simulation.fund_manager import FundManagerFactory
        try:
            FundManagerFactory.create(
                config.fund_manager_name, 
                config.fund_manager_params,
                config.fund_constraints
            )
        except ValueError as e:
            errors.append(str(e))
        
        return errors
    
    @staticmethod
    def save(config: SimulationConfig, file_path: str | Path) -> None:
        """設定をYAMLファイルに保存"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(config.to_dict(), f, allow_unicode=True, default_flow_style=False)
