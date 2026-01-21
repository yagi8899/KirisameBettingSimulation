"""収益分析ページ"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional
from collections import defaultdict

from betting_simulation.models import SimulationResult


def render():
    """収益分析ページをレンダリング"""
    st.title("📈 収益分析")
    
    result: Optional[SimulationResult] = st.session_state.get("result")
    
    if result is None:
        st.info("👈 サイドバーからデータを読み込み、設定ページでシミュレーションを実行してください")
        return
    
    # タブ構成
    tab1, tab2, tab3, tab4 = st.tabs(["📊 ROI推移", "🎯 的中率分析", "📉 損益分布", "🏇 条件別分析"])
    
    with tab1:
        _render_roi_analysis(result)
    
    with tab2:
        _render_hit_rate_analysis(result)
    
    with tab3:
        _render_profit_distribution(result)
    
    with tab4:
        _render_condition_analysis(result)


def _render_roi_analysis(result: SimulationResult):
    """ROI分析"""
    st.subheader("ROI推移")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 累積ROIを計算
    cumulative_invested = 0
    cumulative_payout = 0
    roi_history = []
    
    for bet in result.bet_history:
        cumulative_invested += bet.ticket.amount
        cumulative_payout += bet.payout
        roi = (cumulative_payout / cumulative_invested * 100) if cumulative_invested > 0 else 100
        roi_history.append(roi)
    
    df = pd.DataFrame({
        "レース": range(1, len(roi_history) + 1),
        "ROI (%)": roi_history,
        "基準 (100%)": [100] * len(roi_history),
    })
    
    st.line_chart(df, x="レース", y=["ROI (%)", "基準 (100%)"], use_container_width=True)
    
    # ROI統計
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("最終ROI", f"{roi_history[-1]:.1f}%")
    with col2:
        st.metric("最高ROI", f"{max(roi_history):.1f}%")
    with col3:
        st.metric("最低ROI", f"{min(roi_history):.1f}%")
    with col4:
        avg_roi = sum(roi_history) / len(roi_history)
        st.metric("平均ROI", f"{avg_roi:.1f}%")


def _render_hit_rate_analysis(result: SimulationResult):
    """的中率分析"""
    st.subheader("的中率推移")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 累積的中率を計算
    total_bets = 0
    total_hits = 0
    hit_rate_history = []
    
    for bet in result.bet_history:
        total_bets += 1
        total_hits += 1 if bet.is_hit else 0
        hit_rate = (total_hits / total_bets * 100) if total_bets > 0 else 0
        hit_rate_history.append(hit_rate)
    
    df = pd.DataFrame({
        "レース": range(1, len(hit_rate_history) + 1),
        "的中率 (%)": hit_rate_history,
    })
    
    st.line_chart(df, x="レース", y="的中率 (%)", use_container_width=True)
    
    # 移動平均的中率
    st.subheader("移動平均的中率（20レース）")
    
    window = 20
    hits = [1 if bet.is_hit else 0 for bet in result.bet_history]
    ma_hit_rate = pd.Series(hits).rolling(window=window).mean() * 100
    
    ma_df = pd.DataFrame({
        "レース": range(1, len(ma_hit_rate) + 1),
        "移動平均的中率 (%)": ma_hit_rate,
    })
    
    st.line_chart(ma_df, x="レース", y="移動平均的中率 (%)", use_container_width=True)
    
    # オッズ別的中率
    st.subheader("オッズ帯別的中率")
    
    odds_bands = {
        "1-2倍": (1, 2),
        "2-5倍": (2, 5),
        "5-10倍": (5, 10),
        "10-20倍": (10, 20),
        "20-50倍": (20, 50),
        "50倍以上": (50, float("inf")),
    }
    
    odds_stats = {}
    for band_name, (low, high) in odds_bands.items():
        bets_in_band = [b for b in result.bet_history if low <= b.ticket.odds < high]
        if bets_in_band:
            hits_in_band = sum(1 for b in bets_in_band if b.is_hit)
            odds_stats[band_name] = {
                "賭け数": len(bets_in_band),
                "的中数": hits_in_band,
                "的中率": hits_in_band / len(bets_in_band) * 100,
            }
    
    if odds_stats:
        odds_df = pd.DataFrame([
            {
                "オッズ帯": band,
                "賭け数": data["賭け数"],
                "的中数": data["的中数"],
                "的中率 (%)": f"{data['的中率']:.1f}",
            }
            for band, data in odds_stats.items()
        ])
        st.dataframe(odds_df, use_container_width=True, hide_index=True)


def _render_profit_distribution(result: SimulationResult):
    """損益分布"""
    st.subheader("損益分布")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 各賭けの損益
    profits = [bet.payout - bet.ticket.amount for bet in result.bet_history]
    
    # ヒストグラム用データ
    df = pd.DataFrame({"損益": profits})
    
    st.bar_chart(df["損益"].value_counts().sort_index())
    
    # 統計
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        wins = sum(1 for p in profits if p > 0)
        st.metric("勝ち回数", f"{wins}回")
    with col2:
        losses = sum(1 for p in profits if p < 0)
        st.metric("負け回数", f"{losses}回")
    with col3:
        avg_win = np.mean([p for p in profits if p > 0]) if any(p > 0 for p in profits) else 0
        st.metric("平均勝ち額", f"¥{int(avg_win):,}")
    with col4:
        avg_loss = np.mean([p for p in profits if p < 0]) if any(p < 0 for p in profits) else 0
        st.metric("平均負け額", f"¥{int(avg_loss):,}")
    
    # 勝敗比率
    st.subheader("勝敗比率")
    
    wins = sum(1 for p in profits if p > 0)
    losses = sum(1 for p in profits if p < 0)
    draws = sum(1 for p in profits if p == 0)
    
    pie_df = pd.DataFrame({
        "結果": ["勝ち", "負け", "引き分け"],
        "回数": [wins, losses, draws],
    })
    
    st.bar_chart(pie_df, x="結果", y="回数", use_container_width=True, horizontal=True)


def _render_condition_analysis(result: SimulationResult):
    """条件別分析"""
    st.subheader("条件別収益分析")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 分析軸選択
    analysis_type = st.selectbox(
        "分析軸",
        ["馬券種別", "距離別", "芝/ダート別", "競馬場別"],
    )
    
    if analysis_type == "馬券種別":
        _analyze_by_ticket_type(result)
    elif analysis_type == "距離別":
        _analyze_by_distance(result)
    elif analysis_type == "芝/ダート別":
        _analyze_by_surface(result)
    elif analysis_type == "競馬場別":
        _analyze_by_track(result)


def _analyze_by_ticket_type(result: SimulationResult):
    """馬券種別分析"""
    stats = defaultdict(lambda: {"invested": 0, "payout": 0, "bets": 0, "hits": 0})
    
    for bet in result.bet_history:
        ticket_type = bet.ticket.ticket_type.value
        stats[ticket_type]["invested"] += bet.ticket.amount
        stats[ticket_type]["payout"] += bet.payout
        stats[ticket_type]["bets"] += 1
        stats[ticket_type]["hits"] += 1 if bet.is_hit else 0
    
    df = pd.DataFrame([
        {
            "馬券種": t,
            "賭け数": s["bets"],
            "的中数": s["hits"],
            "的中率 (%)": f"{s['hits'] / s['bets'] * 100:.1f}" if s["bets"] > 0 else "---",
            "投資額": f"¥{s['invested']:,}",
            "払戻額": f"¥{s['payout']:,}",
            "損益": f"¥{s['payout'] - s['invested']:+,}",
            "ROI (%)": f"{s['payout'] / s['invested'] * 100:.1f}" if s["invested"] > 0 else "---",
        }
        for t, s in sorted(stats.items())
    ])
    
    st.dataframe(df, use_container_width=True, hide_index=True)


def _analyze_by_distance(result: SimulationResult):
    """距離別分析"""
    distance_bands = {
        "短距離 (~1400m)": (0, 1400),
        "マイル (1400-1800m)": (1400, 1800),
        "中距離 (1800-2200m)": (1800, 2200),
        "長距離 (2200m~)": (2200, float("inf")),
    }
    
    stats = defaultdict(lambda: {"invested": 0, "payout": 0, "bets": 0, "hits": 0})
    
    for bet in result.bet_history:
        distance = bet.race.distance
        for band_name, (low, high) in distance_bands.items():
            if low <= distance < high:
                stats[band_name]["invested"] += bet.ticket.amount
                stats[band_name]["payout"] += bet.payout
                stats[band_name]["bets"] += 1
                stats[band_name]["hits"] += 1 if bet.is_hit else 0
                break
    
    df = pd.DataFrame([
        {
            "距離帯": band,
            "賭け数": s["bets"],
            "的中数": s["hits"],
            "的中率 (%)": f"{s['hits'] / s['bets'] * 100:.1f}" if s["bets"] > 0 else "---",
            "損益": f"¥{s['payout'] - s['invested']:+,}",
            "ROI (%)": f"{s['payout'] / s['invested'] * 100:.1f}" if s["invested"] > 0 else "---",
        }
        for band, s in stats.items()
    ])
    
    st.dataframe(df, use_container_width=True, hide_index=True)


def _analyze_by_surface(result: SimulationResult):
    """芝/ダート別分析"""
    stats = defaultdict(lambda: {"invested": 0, "payout": 0, "bets": 0, "hits": 0})
    
    for bet in result.bet_history:
        surface = bet.race.surface.value
        stats[surface]["invested"] += bet.ticket.amount
        stats[surface]["payout"] += bet.payout
        stats[surface]["bets"] += 1
        stats[surface]["hits"] += 1 if bet.is_hit else 0
    
    df = pd.DataFrame([
        {
            "馬場": s,
            "賭け数": data["bets"],
            "的中数": data["hits"],
            "的中率 (%)": f"{data['hits'] / data['bets'] * 100:.1f}" if data["bets"] > 0 else "---",
            "損益": f"¥{data['payout'] - data['invested']:+,}",
            "ROI (%)": f"{data['payout'] / data['invested'] * 100:.1f}" if data["invested"] > 0 else "---",
        }
        for s, data in sorted(stats.items())
    ])
    
    st.dataframe(df, use_container_width=True, hide_index=True)


def _analyze_by_track(result: SimulationResult):
    """競馬場別分析"""
    stats = defaultdict(lambda: {"invested": 0, "payout": 0, "bets": 0, "hits": 0})
    
    for bet in result.bet_history:
        track = bet.race.track
        stats[track]["invested"] += bet.ticket.amount
        stats[track]["payout"] += bet.payout
        stats[track]["bets"] += 1
        stats[track]["hits"] += 1 if bet.is_hit else 0
    
    df = pd.DataFrame([
        {
            "競馬場": t,
            "賭け数": s["bets"],
            "的中数": s["hits"],
            "的中率 (%)": f"{s['hits'] / s['bets'] * 100:.1f}" if s["bets"] > 0 else "---",
            "損益": f"¥{s['payout'] - s['invested']:+,}",
            "ROI (%)": f"{s['payout'] / s['invested'] * 100:.1f}" if s["invested"] > 0 else "---",
        }
        for t, s in sorted(stats.items(), key=lambda x: x[1]["payout"] - x[1]["invested"], reverse=True)
    ])
    
    st.dataframe(df, use_container_width=True, hide_index=True)
