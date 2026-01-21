"""戦略比較ページ"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, Dict, List

from betting_simulation.models import SimulationResult, SimulationMetrics
from betting_simulation.strategy import StrategyFactory
from betting_simulation.fund_manager import FundManagerFactory
from betting_simulation.simulation_engine import SimulationEngine, StrategyComparator


def render():
    """戦略比較ページをレンダリング"""
    st.title("🔄 戦略比較")
    
    races = st.session_state.get("races")
    
    if races is None:
        st.info("👈 サイドバーからデータを読み込んでください")
        return
    
    # タブ構成
    tab1, tab2, tab3 = st.tabs(["📊 戦略比較実行", "📈 比較結果", "🎲 モンテカルロ分析"])
    
    with tab1:
        _render_comparison_setup(races)
    
    with tab2:
        _render_comparison_results()
    
    with tab3:
        _render_monte_carlo(races)


def _render_comparison_setup(races):
    """戦略比較の設定"""
    st.subheader("戦略比較設定")
    
    # 利用可能な戦略
    available_strategies = StrategyFactory.list_strategies()
    
    st.markdown("**比較する戦略を選択:**")
    
    selected_strategies = st.multiselect(
        "戦略",
        available_strategies,
        default=available_strategies[:3] if len(available_strategies) >= 3 else available_strategies,
        label_visibility="collapsed",
    )
    
    if len(selected_strategies) < 2:
        st.warning("2つ以上の戦略を選択してください")
        return
    
    # 共通設定
    st.markdown("---")
    st.markdown("**共通設定:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        initial_fund = st.number_input("初期資金", value=100000, step=10000)
        fund_method = st.selectbox("資金管理方式", ["fixed", "kelly", "percentage"])
    
    with col2:
        bet_amount = st.number_input("賭け金（固定の場合）", value=1000, step=100)
        kelly_fraction = st.slider("ケリー係数（kellyの場合）", 0.1, 1.0, 0.5) if fund_method == "kelly" else 0.5
    
    # 比較実行ボタン
    if st.button("🚀 戦略比較を実行", type="primary", use_container_width=True):
        with st.spinner("比較実行中..."):
            results = _run_comparison(
                races,
                selected_strategies,
                initial_fund,
                fund_method,
                bet_amount,
                kelly_fraction,
            )
            st.session_state.comparison_results = results
            st.success(f"✅ {len(results)}戦略の比較完了！")
            st.rerun()


def _run_comparison(
    races,
    strategies: List[str],
    initial_fund: int,
    fund_method: str,
    bet_amount: int,
    kelly_fraction: float,
) -> Dict[str, SimulationResult]:
    """戦略比較を実行"""
    results = {}
    
    for strategy_name in strategies:
        try:
            strategy = StrategyFactory.create(strategy_name)
            
            if fund_method == "fixed":
                fund_manager = FundManagerFactory.create("fixed", bet_amount=bet_amount)
            elif fund_method == "kelly":
                fund_manager = FundManagerFactory.create("kelly", fraction=kelly_fraction)
            else:
                fund_manager = FundManagerFactory.create("percentage", percentage=0.02)
            
            engine = SimulationEngine(
                strategy=strategy,
                fund_manager=fund_manager,
                initial_fund=initial_fund,
            )
            
            result = engine.run(races)
            results[strategy_name] = result
        except Exception as e:
            st.error(f"戦略 {strategy_name} の実行エラー: {e}")
    
    return results


def _render_comparison_results():
    """比較結果の表示"""
    results: Optional[Dict[str, SimulationResult]] = st.session_state.get("comparison_results")
    
    if results is None or len(results) == 0:
        st.info("まず戦略比較を実行してください")
        return
    
    st.subheader("比較結果")
    
    # メトリクス比較テーブル
    comparison_data = []
    
    for name, result in results.items():
        m = result.metrics
        comparison_data.append({
            "戦略": name,
            "最終資金": f"¥{result.final_fund:,}",
            "利益": f"¥{m.profit:+,}" if m else "---",
            "ROI (%)": f"{m.roi:.1f}" if m else "---",
            "的中率 (%)": f"{m.hit_rate:.1f}" if m else "---",
            "最大DD (%)": f"{m.max_drawdown:.1f}" if m else "---",
            "シャープレシオ": f"{m.sharpe_ratio:.3f}" if m else "---",
            "Go判定": "✅" if (m and m.is_go) else "❌",
        })
    
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 資金推移比較グラフ
    st.subheader("資金推移比較")
    
    fund_data = {"レース": range(max(len(r.fund_history) for r in results.values()))}
    
    for name, result in results.items():
        fund_data[name] = result.fund_history + [result.fund_history[-1]] * (
            len(fund_data["レース"]) - len(result.fund_history)
        )
    
    fund_df = pd.DataFrame(fund_data)
    st.line_chart(fund_df, x="レース", y=list(results.keys()), use_container_width=True)
    
    # ランキング
    st.subheader("🏆 総合ランキング")
    
    # スコア計算（ROI * 的中率 / 最大DD）
    rankings = []
    for name, result in results.items():
        m = result.metrics
        if m:
            score = (m.roi * m.hit_rate) / max(m.max_drawdown, 1)
            rankings.append({"戦略": name, "スコア": score, "ROI": m.roi})
        else:
            rankings.append({"戦略": name, "スコア": 0, "ROI": 0})
    
    rankings.sort(key=lambda x: x["スコア"], reverse=True)
    
    for i, r in enumerate(rankings):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
        st.markdown(f"{medal} **{r['戦略']}** - スコア: {r['スコア']:.1f}, ROI: {r['ROI']:.1f}%")


def _render_monte_carlo(races):
    """モンテカルロ分析"""
    st.subheader("モンテカルロシミュレーション")
    
    # 設定
    col1, col2, col3 = st.columns(3)
    
    with col1:
        strategy_name = st.selectbox(
            "分析戦略",
            StrategyFactory.list_strategies(),
        )
    
    with col2:
        n_simulations = st.number_input("シミュレーション回数", value=100, min_value=10, max_value=1000, step=10)
    
    with col3:
        initial_fund = st.number_input("初期資金（MC）", value=100000, step=10000, key="mc_initial_fund")
    
    if st.button("🎲 モンテカルロ実行", use_container_width=True):
        with st.spinner(f"{n_simulations}回のシミュレーション実行中..."):
            mc_results = _run_monte_carlo(races, strategy_name, n_simulations, initial_fund)
            
            if mc_results:
                _render_monte_carlo_results(mc_results, initial_fund)


def _run_monte_carlo(races, strategy_name: str, n_simulations: int, initial_fund: int) -> List[SimulationResult]:
    """モンテカルロシミュレーション実行"""
    from betting_simulation.simulation_engine import MonteCarloSimulator
    
    try:
        strategy = StrategyFactory.create(strategy_name)
        fund_manager = FundManagerFactory.create("fixed", bet_amount=1000)
        
        simulator = MonteCarloSimulator(
            strategy=strategy,
            fund_manager=fund_manager,
            initial_fund=initial_fund,
            n_simulations=n_simulations,
        )
        
        results = simulator.run(races)
        return results
    except Exception as e:
        st.error(f"モンテカルロエラー: {e}")
        return []


def _render_monte_carlo_results(results: List[SimulationResult], initial_fund: int):
    """モンテカルロ結果の表示"""
    st.markdown("---")
    st.subheader("モンテカルロ結果")
    
    # 最終資金の分布
    final_funds = [r.final_fund for r in results]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("平均最終資金", f"¥{int(np.mean(final_funds)):,}")
    with col2:
        st.metric("中央値", f"¥{int(np.median(final_funds)):,}")
    with col3:
        st.metric("最高値", f"¥{int(np.max(final_funds)):,}")
    with col4:
        st.metric("最低値", f"¥{int(np.min(final_funds)):,}")
    
    # パーセンタイル
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("5%パーセンタイル", f"¥{int(np.percentile(final_funds, 5)):,}")
    with col6:
        st.metric("25%パーセンタイル", f"¥{int(np.percentile(final_funds, 25)):,}")
    with col7:
        st.metric("75%パーセンタイル", f"¥{int(np.percentile(final_funds, 75)):,}")
    with col8:
        st.metric("95%パーセンタイル", f"¥{int(np.percentile(final_funds, 95)):,}")
    
    # 破産確率
    bankruptcy_line = initial_fund * 0.1  # 10%を破産ラインとする
    bankruptcy_count = sum(1 for f in final_funds if f <= bankruptcy_line)
    bankruptcy_prob = bankruptcy_count / len(final_funds) * 100
    
    st.metric("破産確率（資金10%以下）", f"{bankruptcy_prob:.1f}%")
    
    # 最終資金分布のヒストグラム
    st.subheader("最終資金分布")
    
    df = pd.DataFrame({"最終資金": final_funds})
    st.bar_chart(df["最終資金"].value_counts().sort_index())
    
    # 信頼区間
    st.subheader("信頼区間")
    
    ci_90 = (np.percentile(final_funds, 5), np.percentile(final_funds, 95))
    ci_80 = (np.percentile(final_funds, 10), np.percentile(final_funds, 90))
    
    st.markdown(f"""
    - **90%信頼区間**: ¥{int(ci_90[0]):,} ～ ¥{int(ci_90[1]):,}
    - **80%信頼区間**: ¥{int(ci_80[0]):,} ～ ¥{int(ci_80[1]):,}
    """)
