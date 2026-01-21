"""リスク分析ページ"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional

from betting_simulation.models import SimulationResult


def render():
    """リスク分析ページをレンダリング"""
    st.title("⚠️ リスク分析")
    
    result: Optional[SimulationResult] = st.session_state.get("result")
    
    if result is None:
        st.info("👈 サイドバーからデータを読み込み、設定ページでシミュレーションを実行してください")
        return
    
    # メトリクス表示
    _render_risk_metrics(result)
    
    st.markdown("---")
    
    # タブ構成
    tab1, tab2, tab3, tab4 = st.tabs(["📉 ドローダウン", "🔥 連敗分析", "📊 ボラティリティ", "🎯 VaR分析"])
    
    with tab1:
        _render_drawdown_analysis(result)
    
    with tab2:
        _render_streak_analysis(result)
    
    with tab3:
        _render_volatility_analysis(result)
    
    with tab4:
        _render_var_analysis(result)


def _render_risk_metrics(result: SimulationResult):
    """リスクメトリクスを表示"""
    metrics = result.metrics
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        max_dd = metrics.max_drawdown if metrics else 0
        st.metric(
            "最大ドローダウン",
            f"{max_dd:.1f}%",
            help="ピークからの最大下落率",
        )
    
    with col2:
        max_loss = metrics.max_consecutive_losses if metrics else 0
        st.metric(
            "最大連敗",
            f"{max_loss}回",
            help="連続で負けた最大回数",
        )
    
    with col3:
        sharpe = metrics.sharpe_ratio if metrics else 0
        st.metric(
            "シャープレシオ",
            f"{sharpe:.3f}",
            help="リスク調整後リターン",
        )
    
    with col4:
        # 破産確率の簡易推定
        if result.fund_history:
            below_half = sum(1 for f in result.fund_history if f < result.initial_fund * 0.5)
            bankruptcy_risk = below_half / len(result.fund_history) * 100
            st.metric(
                "資金半減リスク",
                f"{bankruptcy_risk:.1f}%",
                help="資金が初期の50%を下回った割合",
            )


def _render_drawdown_analysis(result: SimulationResult):
    """ドローダウン分析"""
    st.subheader("ドローダウン推移")
    
    if not result.fund_history:
        st.info("資金履歴がありません")
        return
    
    # ドローダウン計算
    drawdowns = []
    peak = result.fund_history[0]
    
    for fund in result.fund_history:
        if fund > peak:
            peak = fund
        dd = (peak - fund) / peak * 100 if peak > 0 else 0
        drawdowns.append(dd)
    
    df = pd.DataFrame({
        "レース": range(len(drawdowns)),
        "ドローダウン (%)": drawdowns,
    })
    
    st.area_chart(df, x="レース", y="ドローダウン (%)", use_container_width=True)
    
    # ドローダウン統計
    st.subheader("ドローダウン統計")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("最大DD", f"{max(drawdowns):.1f}%")
    with col2:
        st.metric("平均DD", f"{np.mean(drawdowns):.1f}%")
    with col3:
        # DD 10%以上の期間
        over_10 = sum(1 for d in drawdowns if d >= 10)
        st.metric("DD≥10%期間", f"{over_10}回")
    with col4:
        # 回復時間（最大DDからの回復までの期間）
        max_dd_idx = drawdowns.index(max(drawdowns))
        recovery = 0
        for i in range(max_dd_idx, len(drawdowns)):
            if drawdowns[i] == 0:
                recovery = i - max_dd_idx
                break
        if recovery == 0:
            recovery = len(drawdowns) - max_dd_idx
        st.metric("回復期間", f"{recovery}レース")
    
    # ドローダウンヒストグラム
    st.subheader("ドローダウン分布")
    
    dd_df = pd.DataFrame({"ドローダウン": drawdowns})
    st.bar_chart(dd_df["ドローダウン"].value_counts().sort_index())


def _render_streak_analysis(result: SimulationResult):
    """連勝/連敗分析"""
    st.subheader("連勝・連敗分析")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 連勝/連敗を計算
    win_streaks = []
    loss_streaks = []
    
    current_win_streak = 0
    current_loss_streak = 0
    
    for bet in result.bet_history:
        if bet.is_hit:
            current_win_streak += 1
            if current_loss_streak > 0:
                loss_streaks.append(current_loss_streak)
                current_loss_streak = 0
        else:
            current_loss_streak += 1
            if current_win_streak > 0:
                win_streaks.append(current_win_streak)
                current_win_streak = 0
    
    # 最後の連勝/連敗を追加
    if current_win_streak > 0:
        win_streaks.append(current_win_streak)
    if current_loss_streak > 0:
        loss_streaks.append(current_loss_streak)
    
    # メトリクス
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        max_win = max(win_streaks) if win_streaks else 0
        st.metric("最大連勝", f"{max_win}回")
    with col2:
        max_loss = max(loss_streaks) if loss_streaks else 0
        st.metric("最大連敗", f"{max_loss}回")
    with col3:
        avg_win = np.mean(win_streaks) if win_streaks else 0
        st.metric("平均連勝", f"{avg_win:.1f}回")
    with col4:
        avg_loss = np.mean(loss_streaks) if loss_streaks else 0
        st.metric("平均連敗", f"{avg_loss:.1f}回")
    
    # 連勝/連敗の分布
    st.subheader("連勝分布")
    if win_streaks:
        win_df = pd.DataFrame({"連勝数": win_streaks})
        st.bar_chart(win_df["連勝数"].value_counts().sort_index())
    
    st.subheader("連敗分布")
    if loss_streaks:
        loss_df = pd.DataFrame({"連敗数": loss_streaks})
        st.bar_chart(loss_df["連敗数"].value_counts().sort_index())
    
    # 連敗時の損失
    st.subheader("連敗時の累計損失")
    
    current_loss = 0
    max_consecutive_loss = 0
    loss_amounts = []
    
    for bet in result.bet_history:
        if not bet.is_hit:
            current_loss += bet.ticket.amount
            loss_amounts.append(current_loss)
            max_consecutive_loss = max(max_consecutive_loss, current_loss)
        else:
            if current_loss > 0:
                current_loss = 0
    
    st.metric("連敗時最大累計損失", f"¥{max_consecutive_loss:,}")


def _render_volatility_analysis(result: SimulationResult):
    """ボラティリティ分析"""
    st.subheader("ボラティリティ分析")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 損益の変動を分析
    profits = [bet.payout - bet.ticket.amount for bet in result.bet_history]
    
    # ローリングボラティリティ
    window = st.slider("ローリング期間", 5, 50, 20)
    
    rolling_std = pd.Series(profits).rolling(window=window).std()
    
    df = pd.DataFrame({
        "レース": range(len(rolling_std)),
        "ボラティリティ": rolling_std,
    })
    
    st.line_chart(df, x="レース", y="ボラティリティ", use_container_width=True)
    
    # 統計
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("標準偏差", f"¥{int(np.std(profits)):,}")
    with col2:
        st.metric("平均損益", f"¥{int(np.mean(profits)):,}")
    with col3:
        # 変動係数
        cv = np.std(profits) / abs(np.mean(profits)) if np.mean(profits) != 0 else 0
        st.metric("変動係数", f"{cv:.2f}")
    with col4:
        # 尖度（リスクの極端さ）
        from scipy import stats as scipy_stats
        try:
            kurt = scipy_stats.kurtosis(profits)
            st.metric("尖度", f"{kurt:.2f}")
        except:
            st.metric("尖度", "---")


def _render_var_analysis(result: SimulationResult):
    """VaR分析"""
    st.subheader("VaR (Value at Risk) 分析")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 損益データ
    profits = [bet.payout - bet.ticket.amount for bet in result.bet_history]
    
    # VaR計算
    confidence_levels = [0.95, 0.99]
    
    col1, col2 = st.columns(2)
    
    with col1:
        var_95 = np.percentile(profits, 5)  # 下位5%
        st.metric(
            "VaR (95%)",
            f"¥{int(var_95):,}",
            help="95%の確率でこれ以上の損失は発生しない",
        )
    
    with col2:
        var_99 = np.percentile(profits, 1)  # 下位1%
        st.metric(
            "VaR (99%)",
            f"¥{int(var_99):,}",
            help="99%の確率でこれ以上の損失は発生しない",
        )
    
    # CVaR (Expected Shortfall)
    st.subheader("CVaR (Conditional VaR)")
    
    col3, col4 = st.columns(2)
    
    with col3:
        cvar_95 = np.mean([p for p in profits if p <= var_95])
        st.metric(
            "CVaR (95%)",
            f"¥{int(cvar_95):,}" if not np.isnan(cvar_95) else "---",
            help="VaRを超える損失の期待値",
        )
    
    with col4:
        cvar_99 = np.mean([p for p in profits if p <= var_99])
        st.metric(
            "CVaR (99%)",
            f"¥{int(cvar_99):,}" if not np.isnan(cvar_99) else "---",
            help="VaRを超える損失の期待値",
        )
    
    # 損益分布とVaRライン
    st.subheader("損益分布とVaRライン")
    
    df = pd.DataFrame({"損益": profits})
    
    # 損益のヒストグラムデータ
    hist_data = df["損益"].value_counts().sort_index()
    st.bar_chart(hist_data)
    
    st.markdown(f"""
    **VaRの解釈:**
    - VaR(95%) = ¥{int(var_95):,}: 20回に1回程度、これより大きな損失が発生する可能性
    - VaR(99%) = ¥{int(var_99):,}: 100回に1回程度、これより大きな損失が発生する可能性
    """)
