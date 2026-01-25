"""設定ページ"""

import streamlit as st
import json
import tempfile
from pathlib import Path
from typing import Optional

from betting_simulation.config import SimulationConfig
from betting_simulation.strategy import StrategyFactory
from betting_simulation.fund_manager import FundManagerFactory
from betting_simulation.simulation_engine import SimulationEngine
from betting_simulation.reports import ReportGenerator
from betting_simulation.models import SimulationResult


def render():
    """設定ページをレンダリング"""
    st.title("⚙️ 設定 & エクスポート")
    
    # タブ構成
    tab1, tab2, tab3 = st.tabs(["🎮 シミュレーション設定", "📤 エクスポート", "📝 設定ファイル"])
    
    with tab1:
        _render_simulation_settings()
    
    with tab2:
        _render_export_settings()
    
    with tab3:
        _render_config_file()


def _render_simulation_settings():
    """シミュレーション設定"""
    st.subheader("シミュレーション設定")
    
    races = st.session_state.get("races")
    
    if races is None:
        st.warning("⚠️ 先にサイドバーからデータを読み込んでください")
    else:
        st.info(f"📊 {len(races)}レースのデータが読み込まれています")
    
    st.markdown("---")
    
    # 基本設定
    st.markdown("### 基本設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        initial_fund = st.number_input(
            "初期資金",
            value=100000,
            step=10000,
            min_value=10000,
            help="シミュレーション開始時の資金",
        )
    
    with col2:
        bankruptcy_line = st.number_input(
            "破産ライン（%）",
            value=10,
            min_value=0,
            max_value=100,
            help="この割合を下回ったらシミュレーション終了",
        )
    
    st.markdown("---")
    
    # 戦略設定
    st.markdown("### 戦略設定")
    
    # 戦略一覧を取得（日本語説明のみ表示）
    strategies = StrategyFactory.list_strategies()
    # description -> name のマッピングを作成
    description_to_name = {s["description"]: s["name"] for s in strategies}
    strategy_descriptions = [s["description"] for s in strategies]
    
    selected_description = st.selectbox(
        "戦略",
        strategy_descriptions,
        help="使用する賭け戦略を選択",
    )
    
    # 選択された説明からnameを取得
    strategy_name = description_to_name.get(selected_description, "favorite_win")
    
    # 戦略別パラメータ
    strategy_params = _get_strategy_params(strategy_name)
    
    st.markdown("---")
    
    # 資金管理設定
    st.markdown("### 資金管理設定")
    
    fund_manager_options = {
        "定額方式": "fixed",
        "ケリー基準": "kelly",
        "定率方式": "percentage",
    }
    
    selected_fund_label = st.selectbox(
        "資金管理方式",
        list(fund_manager_options.keys()),
        help="賭け金の決定方式",
    )
    
    fund_method = fund_manager_options[selected_fund_label]
    
    fund_params = _get_fund_params(fund_method)
    
    st.markdown("---")
    
    # 設定の保存
    if st.button("💾 設定を保存", use_container_width=True):
        config = SimulationConfig(
            initial_fund=initial_fund,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            fund_manager_name=fund_method,
            fund_manager_params=fund_params,
        )
        st.session_state.config = config
        st.success("✅ 設定を保存しました")
    
    # シミュレーション実行
    st.markdown("---")
    
    if st.button("🚀 シミュレーション実行", type="primary", use_container_width=True):
        if races is None:
            st.error("❌ データを先に読み込んでください")
            return
        
        # 設定をSimulationConfigに保存
        config = SimulationConfig(
            initial_fund=initial_fund,
            bankruptcy_ratio=bankruptcy_line / 100,  # パーセントを小数に変換
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            fund_manager_name=fund_method,
            fund_manager_params=fund_params,
        )
        st.session_state.config = config
        
        with st.spinner("シミュレーション実行中..."):
            try:
                # 戦略作成
                strategy = StrategyFactory.create(strategy_name, strategy_params)
                
                # 資金管理作成
                fund_manager = FundManagerFactory.create(fund_method, fund_params)
                
                # シミュレーションエンジン作成
                engine = SimulationEngine(
                    strategy=strategy,
                    fund_manager=fund_manager,
                )
                
                # 破産ラインを計算（初期資金 × 破産ライン%）
                bankruptcy_threshold = int(initial_fund * config.bankruptcy_ratio)
                
                # シミュレーション実行
                result = engine.run_simple(races, initial_fund, bankruptcy_threshold)
                st.session_state.result = result
                
                st.success(f"✅ シミュレーション完了！最終資金: ¥{result.final_fund:,}")
                
                # 簡易結果表示
                if result.metrics:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("ROI", f"{result.metrics.roi:.1f}%")
                    with col2:
                        st.metric("的中率", f"{result.metrics.hit_rate:.1f}%")
                    with col3:
                        st.metric("利益", f"¥{result.metrics.profit:+,}")
                
            except Exception as e:
                st.error(f"❌ シミュレーションエラー: {e}")


def _get_strategy_params(strategy_name: str) -> dict:
    """戦略パラメータを取得"""
    params = {}
    
    if strategy_name == "favorite_win":
        col1, col2 = st.columns(2)
        with col1:
            params["top_n"] = st.slider("上位N頭", 1, 5, 1)
        with col2:
            params["min_odds"] = st.number_input("最低オッズ", value=1.5, step=0.1)
    
    elif strategy_name == "value_win":
        col1, col2 = st.columns(2)
        with col1:
            params["min_expected_value"] = st.number_input("最低期待値", value=1.0, step=0.1)
        with col2:
            params["max_tickets"] = st.slider("最大馬券数", 1, 10, 3)
    
    elif strategy_name == "box_quinella":
        params["box_size"] = st.slider("上位N頭（馬連ボックス）", 2, 5, 3)
    
    elif strategy_name == "wheel_quinella":
        col1, col2 = st.columns(2)
        with col1:
            params["num_axis"] = st.slider("軸馬数", 1, 3, 1)
        with col2:
            params["num_partners"] = st.slider("相手馬数", 2, 10, 5)
    
    elif strategy_name == "box_wide":
        params["box_size"] = st.slider("上位N頭（ワイドボックス）", 2, 5, 3)
    
    elif strategy_name == "box_trio":
        params["box_size"] = st.slider("上位N頭（3連複ボックス）", 3, 6, 4)
    
    return params


def _get_fund_params(fund_method: str) -> dict:
    """資金管理パラメータを取得"""
    params = {}
    
    if fund_method == "fixed":
        params["bet_amount"] = st.number_input(
            "固定賭け金",
            value=1000,
            step=100,
            min_value=100,
        )
    
    elif fund_method == "kelly":
        col1, col2 = st.columns(2)
        with col1:
            params["fraction"] = st.slider("ケリー係数", 0.1, 1.0, 0.5, 0.1)
        with col2:
            params["max_bet_ratio"] = st.slider("最大賭け率", 0.01, 0.20, 0.05, 0.01)
    
    elif fund_method == "percentage":
        params["percentage"] = st.slider("資金に対する割合", 0.01, 0.10, 0.02, 0.01)
    
    return params


def _render_export_settings():
    """エクスポート設定"""
    st.subheader("結果エクスポート")
    
    result: Optional[SimulationResult] = st.session_state.get("result")
    
    if result is None:
        st.info("シミュレーション結果がありません。先にシミュレーションを実行してください。")
        return
    
    st.markdown("---")
    
    # エクスポート形式選択
    st.markdown("### エクスポート形式")
    
    export_json = st.checkbox("JSON", value=True)
    export_csv = st.checkbox("CSV", value=True)
    export_txt = st.checkbox("テキストレポート", value=True)
    include_history = st.checkbox("賭け履歴を含む", value=False)
    
    st.markdown("---")
    
    # エクスポート実行
    if st.button("📥 レポートを生成", use_container_width=True):
        formats = []
        if export_json:
            formats.append("json")
        if export_csv:
            formats.append("csv")
        if export_txt:
            formats.append("txt")
        
        if not formats:
            st.warning("少なくとも1つの形式を選択してください")
            return
        
        with st.spinner("レポート生成中..."):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    generator = ReportGenerator(Path(tmpdir))
                    paths = generator.generate(result, formats=formats, include_history=include_history)
                    
                    st.success(f"✅ {len(paths)}ファイル生成完了！")
                    
                    # ダウンロードボタン
                    for path in paths:
                        with open(path, "rb") as f:
                            st.download_button(
                                f"📥 {path.name}",
                                f.read(),
                                file_name=path.name,
                                use_container_width=True,
                            )
            except Exception as e:
                st.error(f"エクスポートエラー: {e}")


def _render_config_file():
    """設定ファイル管理"""
    st.subheader("設定ファイル")
    
    # 現在の設定を表示
    config = st.session_state.get("config")
    
    if config:
        st.markdown("### 現在の設定")
        
        config_dict = {
            "initial_fund": config.initial_fund,
            "strategy": {
                "name": config.strategy_name,
                "params": config.strategy_params,
            },
            "fund": {
                "method": config.fund_manager_name,
                "params": config.fund_manager_params,
            },
        }
        
        st.json(config_dict)
        
        # 設定ファイルダウンロード
        config_json = json.dumps(config_dict, indent=2, ensure_ascii=False)
        st.download_button(
            "📥 設定ファイルをダウンロード",
            config_json,
            file_name="simulation_config.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.info("設定がありません。シミュレーション設定タブで設定を作成してください。")
    
    st.markdown("---")
    
    # 設定ファイルのアップロード
    st.markdown("### 設定ファイルのインポート")
    
    uploaded_config = st.file_uploader(
        "設定ファイル（JSON）",
        type=["json"],
        help="以前保存した設定ファイルをアップロード",
    )
    
    if uploaded_config is not None:
        try:
            config_dict = json.load(uploaded_config)
            st.json(config_dict)
            
            if st.button("📤 この設定を適用", use_container_width=True):
                config = SimulationConfig(
                    initial_fund=config_dict["initial_fund"],
                    strategy_name=config_dict["strategy"]["name"],
                    strategy_params=config_dict["strategy"].get("params", {}),
                    fund_manager_name=config_dict["fund"]["method"],
                    fund_manager_params=config_dict["fund"].get("params", {}),
                )
                st.session_state.config = config
                st.success("✅ 設定を適用しました")
                st.rerun()
        except Exception as e:
            st.error(f"設定ファイルの読み込みエラー: {e}")
