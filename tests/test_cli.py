"""CLIのテスト"""

import pytest
from click.testing import CliRunner

from betting_simulation.cli import main


@pytest.fixture
def runner():
    """CLIランナー"""
    return CliRunner()


class TestCLI:
    """CLIコマンドのテスト"""
    
    def test_version(self, runner):
        """バージョン表示"""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
    
    def test_list_strategies(self, runner):
        """戦略一覧"""
        result = runner.invoke(main, ["list-strategies"])
        assert result.exit_code == 0
        assert "favorite_win" in result.output
        assert "box_quinella" in result.output
    
    def test_list_fund_managers(self, runner):
        """資金管理一覧"""
        result = runner.invoke(main, ["list-fund-managers"])
        assert result.exit_code == 0
        assert "fixed" in result.output
        assert "percentage" in result.output
    
    def test_init_config(self, runner, tmp_path):
        """設定ファイル生成"""
        output = tmp_path / "config.yaml"
        result = runner.invoke(main, ["init-config", str(output)])
        
        assert result.exit_code == 0
        assert output.exists()
    
    def test_validate_valid_config(self, runner, tmp_path):
        """有効な設定の検証"""
        # ダミーのTSVファイルを作成
        tsv_path = tmp_path / "test.tsv"
        tsv_path.write_text("header1\theader2\n", encoding="utf-8")
        
        config_content = f"""data_path: "{tsv_path.as_posix()}"
strategy_name: "favorite_win"
strategy_params:
  top_n: 1
fund_manager_name: "fixed"
fund_manager_params:
  bet_amount: 1000
initial_fund: 100000
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content, encoding="utf-8")
        
        result = runner.invoke(main, ["validate", str(config_path)])
        
        assert result.exit_code == 0, f"Validation failed: {result.output}"
        assert "valid" in result.output.lower()
    
    def test_validate_invalid_config(self, runner, tmp_path):
        """無効な設定の検証"""
        config_content = """
data_path: "test.tsv"
strategy_name: "unknown_strategy"
initial_fund: 100000
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content, encoding="utf-8")
        
        result = runner.invoke(main, ["validate", str(config_path)])
        
        assert result.exit_code != 0
    
    def test_run_missing_data(self, runner, tmp_path):
        """存在しないデータファイルでエラー"""
        config_content = """
data_path: "nonexistent.tsv"
strategy_name: "favorite_win"
strategy_params:
  top_n: 1
fund_manager_name: "fixed"
fund_manager_params:
  bet_amount: 1000
initial_fund: 100000
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content, encoding="utf-8")
        
        result = runner.invoke(main, ["run", str(config_path)])
        
        assert result.exit_code != 0
        assert "Error" in result.output or "error" in result.output.lower()


class TestCompareCommand:
    """compareコマンドのテスト"""
    
    def test_compare_needs_two_configs(self, runner, tmp_path):
        """比較には2つ以上の設定が必要"""
        config_content = """
data_path: "test.tsv"
strategy_name: "favorite_win"
strategy_params:
  top_n: 1
fund_manager_name: "fixed"
fund_manager_params:
  bet_amount: 1000
initial_fund: 100000
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content, encoding="utf-8")
        
        result = runner.invoke(main, ["compare", str(config_path)])
        
        assert result.exit_code != 0
        assert "2" in result.output  # "At least 2 config files"
    
    def test_compare_help(self, runner):
        """compareヘルプ表示"""
        result = runner.invoke(main, ["compare", "--help"])
        
        assert result.exit_code == 0
        assert "compare" in result.output.lower()
        assert "--sort-by" in result.output
        assert "--walk-forward" in result.output
