"""資金推移ページ"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional

from betting_simulation.models import SimulationResult


def render():
    """資金推移ページをレンダリング"""
    st.title("💰 資金推移分析")
    
    result: Optional[SimulationResult] = st.session_state.get("result")
    
    if result is None:
        st.info("👈 サイドバーからデータを読み込み、設定ページでシミュレーションを実行してください")
        return
    
    # タブ構成
    tab1, tab2, tab3 = st.tabs(["📈 資金推移", "📊 日別分析", "🔥 ヒートマップ"])
    
    with tab1:
        _render_fund_transition(result)
    
    with tab2:
        _render_daily_analysis(result)
    
    with tab3:
        _render_heatmap(result)


def _render_fund_transition(result: SimulationResult):
    """資金推移グラフ"""
    st.subheader("資金推移グラフ")
    
    # オプション
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_ma = st.checkbox("移動平均を表示", value=True)
        ma_window = st.slider("移動平均期間", 5, 50, 20) if show_ma else 20
    
    with col2:
        show_target = st.checkbox("目標ラインを表示", value=False)
        target = st.number_input("目標金額", value=result.initial_fund * 2) if show_target else None
    
    with col3:
        show_drawdown = st.checkbox("ドローダウンを表示", value=False)
    
    # データ準備
    df = pd.DataFrame({
        "レース": range(len(result.fund_history)),
        "資金": result.fund_history,
    })
    
    if show_ma:
        df["移動平均"] = pd.Series(result.fund_history).rolling(window=ma_window).mean()
    
    if show_target:
        df["目標"] = target
    
    # グラフ描画
    y_columns = ["資金"]
    if show_ma:
        y_columns.append("移動平均")
    if show_target:
        y_columns.append("目標")
    
    st.line_chart(df, x="レース", y=y_columns, use_container_width=True)
    
    # ドローダウン表示
    if show_drawdown:
        st.subheader("ドローダウン推移")
        drawdowns = _calculate_drawdown(result.fund_history)
        dd_df = pd.DataFrame({
            "レース": range(len(drawdowns)),
            "ドローダウン (%)": [d * 100 for d in drawdowns],
        })
        st.area_chart(dd_df, x="レース", y="ドローダウン (%)", use_container_width=True)
    
    # 統計情報
    st.markdown("---")
    _render_fund_stats(result)


def _calculate_drawdown(fund_history: list) -> list:
    """ドローダウンを計算"""
    drawdowns = []
    peak = fund_history[0]
    
    for fund in fund_history:
        if fund > peak:
            peak = fund
        dd = (peak - fund) / peak if peak > 0 else 0
        drawdowns.append(dd)
    
    return drawdowns


def _render_fund_stats(result: SimulationResult):
    """資金統計情報"""
    st.subheader("📊 資金統計")
    
    fund_array = np.array(result.fund_history)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("最高値", f"¥{int(fund_array.max()):,}")
    with col2:
        st.metric("最低値", f"¥{int(fund_array.min()):,}")
    with col3:
        st.metric("平均値", f"¥{int(fund_array.mean()):,}")
    with col4:
        st.metric("標準偏差", f"¥{int(fund_array.std()):,}")
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        max_dd = max(_calculate_drawdown(result.fund_history)) * 100
        st.metric("最大ドローダウン", f"{max_dd:.1f}%")
    with col6:
        volatility = (fund_array.std() / fund_array.mean()) * 100
        st.metric("ボラティリティ", f"{volatility:.1f}%")
    with col7:
        growth = (result.final_fund / result.initial_fund - 1) * 100
        st.metric("資金成長率", f"{growth:+.1f}%")
    with col8:
        # 初期資金を下回った回数
        below_initial = sum(1 for f in result.fund_history if f < result.initial_fund)
        st.metric("元本割れ回数", f"{below_initial}回")


def _render_daily_analysis(result: SimulationResult):
    """日別分析"""
    st.subheader("📅 日別資金推移")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 日別に集計
    daily_data = {}
    for bet in result.bet_history:
        date_key = f"{bet.race.year}/{bet.race.kaisai_date:04d}"
        if date_key not in daily_data:
            daily_data[date_key] = {
                "profit": 0,
                "bets": 0,
                "hits": 0,
                "final_fund": bet.fund_after,
            }
        daily_data[date_key]["profit"] += bet.payout - bet.ticket.amount
        daily_data[date_key]["bets"] += 1
        daily_data[date_key]["hits"] += 1 if bet.is_hit else 0
        daily_data[date_key]["final_fund"] = bet.fund_after
    
    # DataFrameに変換
    df = pd.DataFrame([
        {
            "日付": date,
            "損益": data["profit"],
            "賭け数": data["bets"],
            "的中数": data["hits"],
            "最終資金": data["final_fund"],
        }
        for date, data in daily_data.items()
    ])
    
    if df.empty:
        st.info("日別データがありません")
        return
    
    # 日別損益グラフ
    st.bar_chart(df, x="日付", y="損益", use_container_width=True)
    
    # 日別テーブル
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_heatmap(result: SimulationResult):
    """資金ヒートマップ"""
    st.subheader("🔥 資金ヒートマップ")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 競馬場別・月別の集計
    track_monthly = {}
    
    for bet in result.bet_history:
        track = bet.race.track
        month = f"{bet.race.kaisai_date:04d}"[:2]  # MMDDの先頭2桁
        
        key = (track, month)
        if key not in track_monthly:
            track_monthly[key] = 0
        track_monthly[key] += bet.payout - bet.ticket.amount
    
    if not track_monthly:
        st.info("データがありません")
        return
    
    # ピボットテーブル形式に変換
    tracks = sorted(set(k[0] for k in track_monthly.keys()))
    months = sorted(set(k[1] for k in track_monthly.keys()))
    
    data = []
    for track in tracks:
        row = {"競馬場": track}
        for month in months:
            row[f"{month}月"] = track_monthly.get((track, month), 0)
        data.append(row)
    
    df = pd.DataFrame(data)
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 競馬場別の総合成績
    st.subheader("🏇 競馬場別成績")
    
    track_summary = {}
    for bet in result.bet_history:
        track = bet.race.track
        if track not in track_summary:
            track_summary[track] = {"profit": 0, "bets": 0, "hits": 0}
        track_summary[track]["profit"] += bet.payout - bet.ticket.amount
        track_summary[track]["bets"] += 1
        track_summary[track]["hits"] += 1 if bet.is_hit else 0
    
    track_df = pd.DataFrame([
        {
            "競馬場": track,
            "損益": data["profit"],
            "賭け数": data["bets"],
            "的中数": data["hits"],
            "的中率": f"{data['hits'] / data['bets'] * 100:.1f}%" if data["bets"] > 0 else "---",
        }
        for track, data in sorted(track_summary.items(), key=lambda x: x[1]["profit"], reverse=True)
    ])
    
    st.dataframe(track_df, use_container_width=True, hide_index=True)
