"""Streamlitダッシュボードのメインアプリ"""

import streamlit as st
from pathlib import Path
from typing import Optional
import sys

# パス設定
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from betting_simulation.data_loader import DataLoader
from betting_simulation.config import SimulationConfig
from betting_simulation.simulation_engine import SimulationEngine, StrategyComparator
from betting_simulation.strategy import StrategyFactory
from betting_simulation.fund_manager import FundManagerFactory
from betting_simulation.models import SimulationResult


def init_session_state():
    """セッション状態を初期化"""
    if "config" not in st.session_state:
        st.session_state.config = None
    if "races" not in st.session_state:
        st.session_state.races = None
    if "result" not in st.session_state:
        st.session_state.result = None
    if "comparison_results" not in st.session_state:
        st.session_state.comparison_results = None


def load_data(file_path: Path) -> bool:
    """データを読み込む"""
    try:
        loader = DataLoader()
        st.session_state.races = loader.load(file_path)
        return True
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return False


def run_simulation() -> Optional[SimulationResult]:
    """シミュレーションを実行"""
    if st.session_state.races is None:
        st.error("先にデータを読み込んでください")
        return None
    
    if st.session_state.config is None:
        st.error("先に設定を行ってください")
        return None
    
    try:
        config = st.session_state.config
        strategy = StrategyFactory.create(
            config.strategy.name,
            **config.strategy.params
        )
        fund_manager = FundManagerFactory.create(
            config.fund.method,
            **config.fund.params
        )
        
        engine = SimulationEngine(
            strategy=strategy,
            fund_manager=fund_manager,
            initial_fund=config.initial_fund,
        )
        
        result = engine.run(st.session_state.races)
        st.session_state.result = result
        return result
    except Exception as e:
        st.error(f"シミュレーションエラー: {e}")
        return None


def main():
    """メインアプリ"""
    st.set_page_config(
        page_title="競馬賭けシミュレーター",
        page_icon="🏇",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    init_session_state()
    
    # サイドバー
    with st.sidebar:
        st.title("🏇 競馬シミュレーター")
        st.markdown("---")
        
        # ナビゲーション
        page = st.radio(
            "ページ選択",
            ["📊 サマリー", "💰 資金推移", "📈 収益分析", "⚠️ リスク分析", "🔄 戦略比較", "⚙️ 設定"],
            label_visibility="collapsed",
        )
        
        st.markdown("---")
        
        # データ読み込み
        st.subheader("📁 データ読み込み")
        uploaded_file = st.file_uploader(
            "予測結果ファイル（TSV）",
            type=["tsv", "txt"],
            help="予測システムから出力されたTSVファイルをアップロード",
        )
        
        if uploaded_file is not None:
            # 一時ファイルに保存
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tsv") as f:
                f.write(uploaded_file.getvalue())
                temp_path = Path(f.name)
            
            if st.button("データ読み込み", use_container_width=True):
                with st.spinner("読み込み中..."):
                    if load_data(temp_path):
                        st.success(f"✅ {len(st.session_state.races)}レース読み込み完了")
        
        # 読み込み済みデータの情報
        if st.session_state.races is not None:
            st.info(f"📊 {len(st.session_state.races)}レース読み込み済み")
        
        st.markdown("---")
        st.caption("v0.1.0 | Phase 4 Dashboard")
    
    # メインコンテンツ
    if page == "📊 サマリー":
        from .pages import summary_page
        summary_page.render()
    elif page == "💰 資金推移":
        from .pages import fund_page
        fund_page.render()
    elif page == "📈 収益分析":
        from .pages import profit_page
        profit_page.render()
    elif page == "⚠️ リスク分析":
        from .pages import risk_page
        risk_page.render()
    elif page == "🔄 戦略比較":
        from .pages import strategy_page
        strategy_page.render()
    elif page == "⚙️ 設定":
        from .pages import settings_page
        settings_page.render()


def run_dashboard():
    """ダッシュボードを起動"""
    import subprocess
    import sys
    
    app_path = Path(__file__).resolve()
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])


if __name__ == "__main__":
    main()
