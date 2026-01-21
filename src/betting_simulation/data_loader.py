"""データローダー

TSVファイルからレースデータを読み込む。
"""

import logging
from pathlib import Path

import pandas as pd

from betting_simulation.models import Horse, Race, RacePayouts, Surface

logger = logging.getLogger(__name__)


class DataLoader:
    """TSVファイルからレースデータを読み込むクラス"""
    
    # 必須カラム
    REQUIRED_COLUMNS = [
        "競馬場", "開催年", "開催日", "レース番号", "芝ダ区分", "距離",
        "馬番", "馬名", "単勝オッズ", "人気順", "確定着順", "予測順位", "予測スコア"
    ]
    
    # 払戻関連カラム
    PAYOUT_COLUMNS = [
        "複勝1着馬番", "複勝1着オッズ", "複勝1着人気",
        "複勝2着馬番", "複勝2着オッズ", "複勝2着人気",
        "複勝3着馬番", "複勝3着オッズ", "複勝3着人気",
        "馬連馬番1", "馬連馬番2", "馬連オッズ",
        "ワイド1_2馬番1", "ワイド1_2馬番2", "ワイド1_2オッズ",
        "ワイド2_3着馬番1", "ワイド2_3着馬番2", "ワイド2_3オッズ",
        "ワイド1_3着馬番1", "ワイド1_3着馬番2", "ワイド1_3オッズ",
        "馬単馬番1", "馬単馬番2", "馬単オッズ",
        "３連複オッズ"
    ]
    
    def __init__(self) -> None:
        """初期化"""
        pass
    
    def load(self, file_path: str | Path) -> list[Race]:
        """TSVファイルを読み込んでRaceリストを返す
        
        Args:
            file_path: TSVファイルパス
            
        Returns:
            Raceオブジェクトのリスト
            
        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: 必須カラムが欠けている場合
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Loading data from {file_path}")
        
        # ファイルサイズチェック
        if file_path.stat().st_size == 0:
            logger.warning("Empty file")
            return []
        
        # TSV読み込み
        try:
            df = pd.read_csv(file_path, sep="\t", encoding="utf-8")
        except pd.errors.EmptyDataError:
            logger.warning("Empty file or no data")
            return []
        
        if df.empty:
            logger.warning("Empty file")
            return []
        
        # 必須カラムチェック
        self._validate_columns(df)
        
        # レースごとにグループ化してRaceオブジェクト作成
        races = self._build_races(df)
        
        logger.info(f"Loaded {len(races)} races")
        return races
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """必須カラムの存在確認"""
        missing = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"必須カラムが不足しています: {missing}")
    
    def _build_races(self, df: pd.DataFrame) -> list[Race]:
        """DataFrameからRaceオブジェクトを構築"""
        races = []
        
        # レースキーでグループ化
        group_keys = ["競馬場", "開催年", "開催日", "レース番号"]
        
        for (track, year, kaisai_date, race_number), group in df.groupby(group_keys):
            try:
                race = self._build_race(track, year, kaisai_date, race_number, group)
                races.append(race)
            except Exception as e:
                logger.warning(
                    f"Failed to build race {track}_{year}_{kaisai_date}_{race_number}: {e}"
                )
                continue
        
        return races
    
    def _build_race(
        self, 
        track: str, 
        year: int, 
        kaisai_date: int, 
        race_number: int, 
        group: pd.DataFrame
    ) -> Race:
        """1レース分のRaceオブジェクトを構築"""
        # 最初の行からレース情報を取得
        first_row = group.iloc[0]
        surface = Surface.from_str(str(first_row["芝ダ区分"]))
        distance = int(first_row["距離"])
        
        # 馬データを構築
        horses = []
        for _, row in group.iterrows():
            horse = self._build_horse(row)
            if horse:
                horses.append(horse)
        
        # 払戻情報を構築
        payouts = self._build_payouts(first_row)
        
        return Race(
            track=str(track),
            year=int(year),
            kaisai_date=int(kaisai_date),
            race_number=int(race_number),
            surface=surface,
            distance=distance,
            horses=horses,
            payouts=payouts
        )
    
    def _build_horse(self, row: pd.Series) -> Horse | None:
        """1頭分のHorseオブジェクトを構築"""
        try:
            # 穴馬関連（オプション）
            hole_prob = float(row.get("穴馬確率", 0) or 0)
            is_hole_candidate = bool(row.get("穴馬候補", 0))
            is_actual_hole = bool(row.get("実際の穴馬", 0))
            
            return Horse(
                number=int(row["馬番"]),
                name=str(row["馬名"]).strip(),
                odds=float(row["単勝オッズ"]),
                popularity=int(row["人気順"]),
                actual_rank=int(row["確定着順"]),
                predicted_rank=int(row["予測順位"]),
                predicted_score=float(row["予測スコア"]),
                hole_probability=hole_prob,
                is_hole_candidate=is_hole_candidate,
                is_actual_hole=is_actual_hole
            )
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to build horse: {e}")
            return None
    
    def _build_payouts(self, row: pd.Series) -> RacePayouts:
        """払戻情報を構築"""
        payouts = RacePayouts()
        
        try:
            # 複勝（1-3着）
            payouts.place_horses = [
                int(row.get("複勝1着馬番", 0) or 0),
                int(row.get("複勝2着馬番", 0) or 0),
                int(row.get("複勝3着馬番", 0) or 0),
            ]
            payouts.place_payouts = [
                float(row.get("複勝1着オッズ", 0) or 0),
                float(row.get("複勝2着オッズ", 0) or 0),
                float(row.get("複勝3着オッズ", 0) or 0),
            ]
            payouts.place_popularities = [
                int(row.get("複勝1着人気", 0) or 0),
                int(row.get("複勝2着人気", 0) or 0),
                int(row.get("複勝3着人気", 0) or 0),
            ]
            
            # 単勝（1着の情報から）
            payouts.win_horse = payouts.place_horses[0] if payouts.place_horses else 0
            # 単勝オッズは馬のデータから取得するので、ここでは設定しない
            
            # 馬連
            payouts.quinella_horses = (
                int(row.get("馬連馬番1", 0) or 0),
                int(row.get("馬連馬番2", 0) or 0)
            )
            payouts.quinella_payout = float(row.get("馬連オッズ", 0) or 0)
            
            # ワイド（3通り）
            payouts.wide_pairs = [
                (int(row.get("ワイド1_2馬番1", 0) or 0), int(row.get("ワイド1_2馬番2", 0) or 0)),
                (int(row.get("ワイド2_3着馬番1", 0) or 0), int(row.get("ワイド2_3着馬番2", 0) or 0)),
                (int(row.get("ワイド1_3着馬番1", 0) or 0), int(row.get("ワイド1_3着馬番2", 0) or 0)),
            ]
            payouts.wide_payouts = [
                float(row.get("ワイド1_2オッズ", 0) or 0),
                float(row.get("ワイド2_3オッズ", 0) or 0),
                float(row.get("ワイド1_3オッズ", 0) or 0),
            ]
            
            # 馬単
            payouts.exacta_horses = (
                int(row.get("馬単馬番1", 0) or 0),
                int(row.get("馬単馬番2", 0) or 0)
            )
            payouts.exacta_payout = float(row.get("馬単オッズ", 0) or 0)
            
            # 三連複
            # TSVには三連複オッズのみで馬番がないので、複勝1-3着から推測
            payouts.trio_horses = (
                payouts.place_horses[0] if len(payouts.place_horses) > 0 else 0,
                payouts.place_horses[1] if len(payouts.place_horses) > 1 else 0,
                payouts.place_horses[2] if len(payouts.place_horses) > 2 else 0,
            )
            payouts.trio_payout = float(row.get("３連複オッズ", 0) or 0)
            
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to build payouts: {e}")
        
        return payouts
    
    def get_summary(self, races: list[Race]) -> dict:
        """読み込んだデータのサマリーを取得"""
        if not races:
            return {"total_races": 0}
        
        tracks = set(r.track for r in races)
        years = set(r.year for r in races)
        total_horses = sum(r.num_horses for r in races)
        
        return {
            "total_races": len(races),
            "total_horses": total_horses,
            "tracks": sorted(tracks),
            "years": sorted(years),
            "avg_horses_per_race": total_horses / len(races),
        }
