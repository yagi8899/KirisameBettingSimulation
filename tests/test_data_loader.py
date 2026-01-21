"""DataLoaderのユニットテスト"""

import pytest
from pathlib import Path

from betting_simulation.data_loader import DataLoader
from betting_simulation.models import Race, Surface


class TestDataLoader:
    """DataLoaderのテスト"""
    
    @pytest.fixture
    def loader(self):
        return DataLoader()
    
    @pytest.fixture
    def sample_tsv_path(self, tmp_path):
        """テスト用TSVファイル"""
        content = """競馬場\t開催年\t開催日\tレース番号\t芝ダ区分\t距離\t馬番\t馬名\t単勝オッズ\t人気順\t確定着順\t予測順位\t予測スコア\t穴馬確率\t穴馬候補\t実際の穴馬\t複勝1着馬番\t複勝1着オッズ\t複勝1着人気\t複勝2着馬番\t複勝2着オッズ\t複勝2着人気\t複勝3着馬番\t複勝3着オッズ\t複勝3着人気\t馬連馬番1\t馬連馬番2\t馬連オッズ\tワイド1_2馬番1\tワイド1_2馬番2\tワイド2_3着馬番1\tワイド2_3着馬番2\tワイド1_3着馬番1\tワイド1_3着馬番2\tワイド1_2オッズ\tワイド2_3オッズ\tワイド1_3オッズ\t馬単馬番1\t馬単馬番2\t馬単オッズ\t３連複オッズ
東京\t2025\t501\t11\t芝\t1600\t1\tテスト馬1\t3.2\t1\t1\t1\t0.85\t0.1\t0\t0\t1\t1.3\t1\t2\t2.0\t2\t3\t3.5\t3\t1\t2\t550\t1\t2\t2\t3\t1\t3\t180\t320\t250\t1\t2\t1100\t2500
東京\t2025\t501\t11\t芝\t1600\t2\tテスト馬2\t5.5\t2\t2\t2\t0.72\t0.05\t0\t0\t1\t1.3\t1\t2\t2.0\t2\t3\t3.5\t3\t1\t2\t550\t1\t2\t2\t3\t1\t3\t180\t320\t250\t1\t2\t1100\t2500
東京\t2025\t501\t11\t芝\t1600\t3\tテスト馬3\t12.3\t5\t3\t4\t0.58\t0.3\t1\t0\t1\t1.3\t1\t2\t2.0\t2\t3\t3.5\t3\t1\t2\t550\t1\t2\t2\t3\t1\t3\t180\t320\t250\t1\t2\t1100\t2500"""
        
        tsv_file = tmp_path / "test.tsv"
        tsv_file.write_text(content, encoding="utf-8")
        return tsv_file
    
    def test_load_valid_tsv(self, loader, sample_tsv_path):
        """有効なTSVファイルを読み込める"""
        races = loader.load(sample_tsv_path)
        
        assert len(races) == 1
        assert isinstance(races[0], Race)
    
    def test_race_has_correct_metadata(self, loader, sample_tsv_path):
        """レースメタデータが正しい"""
        races = loader.load(sample_tsv_path)
        race = races[0]
        
        assert race.track == "東京"
        assert race.year == 2025
        assert race.race_number == 11
        assert race.surface == Surface.TURF
        assert race.distance == 1600
    
    def test_race_has_horses(self, loader, sample_tsv_path):
        """馬データが読み込まれる"""
        races = loader.load(sample_tsv_path)
        race = races[0]
        
        assert len(race.horses) == 3
        assert race.horses[0].name == "テスト馬1"
        assert race.horses[0].odds == 3.2
        assert race.horses[0].predicted_rank == 1
    
    def test_race_has_payouts(self, loader, sample_tsv_path):
        """払戻情報が読み込まれる"""
        races = loader.load(sample_tsv_path)
        race = races[0]
        
        assert race.payouts is not None
        assert race.payouts.quinella_horses == (1, 2)
        assert race.payouts.quinella_payout == 550
    
    def test_load_nonexistent_file(self, loader):
        """存在しないファイルでエラー"""
        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent.tsv")
    
    def test_load_empty_file(self, loader, tmp_path):
        """空ファイルは空リストを返す"""
        empty_file = tmp_path / "empty.tsv"
        empty_file.write_text("", encoding="utf-8")
        
        races = loader.load(empty_file)
        assert races == []
    
    def test_get_summary(self, loader, sample_tsv_path):
        """サマリーが取得できる"""
        races = loader.load(sample_tsv_path)
        summary = loader.get_summary(races)
        
        assert summary["total_races"] == 1
        assert summary["total_horses"] == 3
        assert "東京" in summary["tracks"]
