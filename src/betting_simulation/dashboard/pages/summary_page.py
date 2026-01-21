"""サマリーページ"""

import streamlit as st
import pandas as pd
from typing import Optional

from betting_simulation.models import SimulationResult, SimulationMetrics


def render():
    """サマリーページをレンダリング"""
    st.title("📊 シミュレーションサマリー")
    
    result: Optional[SimulationResult] = st.session_state.get("result")
    
    if result is None:
        st.info("👈 サイドバーからデータを読み込み、設定ページでシミュレーションを実行してください")
        _render_placeholder()
        return
    
    # メトリクスカード
    _render_metrics_cards(result)
    
    st.markdown("---")
    
    # 2カラムレイアウト
    col1, col2 = st.columns(2)
    
    with col1:
        _render_fund_chart(result)
    
    with col2:
        _render_summary_table(result)
    
    # 詳細セクション
    st.markdown("---")
    _render_bet_history(result)


def _render_placeholder():
    """プレースホルダーを表示"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("最終資金", "---", help="シミュレーション後の資金")
    with col2:
        st.metric("ROI", "---", help="投資利益率")
    with col3:
        st.metric("的中率", "---", help="的中した割合")
    with col4:
        st.metric("総利益", "---", help="純利益")


def _render_metrics_cards(result: SimulationResult):
    """メトリクスカードを表示"""
    metrics = result.metrics
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        profit = result.final_fund - result.initial_fund
        delta_color = "normal" if profit >= 0 else "inverse"
        st.metric(
            "最終資金",
            f"¥{result.final_fund:,}",
            delta=f"¥{profit:+,}",
            delta_color=delta_color,
        )
    
    with col2:
        roi = metrics.roi if metrics else 0
        delta_color = "normal" if roi >= 100 else "inverse"
        st.metric(
            "ROI",
            f"{roi:.1f}%",
            delta=f"{roi - 100:+.1f}%",
            delta_color=delta_color,
        )
    
    with col3:
        hit_rate = metrics.hit_rate if metrics else 0
        st.metric(
            "的中率",
            f"{hit_rate:.1f}%",
            help="賭けが的中した割合",
        )
    
    with col4:
        profit = metrics.profit if metrics else 0
        delta_color = "normal" if profit >= 0 else "inverse"
        st.metric(
            "総利益",
            f"¥{profit:,}",
            delta_color=delta_color,
        )
    
    # 追加メトリクス
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        total_bets = metrics.total_bets if metrics else 0
        st.metric("総賭け回数", f"{total_bets:,}回")
    
    with col6:
        total_hits = metrics.total_hits if metrics else 0
        st.metric("的中回数", f"{total_hits:,}回")
    
    with col7:
        max_dd = metrics.max_drawdown if metrics else 0
        st.metric(
            "最大ドローダウン",
            f"{max_dd:.1f}%",
            help="ピークからの最大下落率",
        )
    
    with col8:
        is_go = metrics.is_go if metrics else False
        status = "✅ Go" if is_go else "❌ No-Go"
        st.metric("Go/No-Go判定", status)


def _render_fund_chart(result: SimulationResult):
    """資金推移チャートを表示"""
    st.subheader("💰 資金推移")
    
    df = pd.DataFrame({
        "レース": range(len(result.fund_history)),
        "資金": result.fund_history,
    })
    
    st.line_chart(df, x="レース", y="資金", use_container_width=True)


def _render_summary_table(result: SimulationResult):
    """サマリーテーブルを表示"""
    st.subheader("📋 詳細サマリー")
    
    metrics = result.metrics
    
    data = {
        "項目": [
            "初期資金",
            "最終資金",
            "総投資額",
            "総払戻額",
            "純利益",
            "ROI",
            "的中率",
            "最大連勝",
            "最大連敗",
            "シャープレシオ",
        ],
        "値": [
            f"¥{result.initial_fund:,}",
            f"¥{result.final_fund:,}",
            f"¥{metrics.total_invested:,}" if metrics else "---",
            f"¥{metrics.total_payout:,}" if metrics else "---",
            f"¥{metrics.profit:,}" if metrics else "---",
            f"{metrics.roi:.2f}%" if metrics else "---",
            f"{metrics.hit_rate:.2f}%" if metrics else "---",
            f"{metrics.max_consecutive_wins}回" if metrics else "---",
            f"{metrics.max_consecutive_losses}回" if metrics else "---",
            f"{metrics.sharpe_ratio:.3f}" if metrics else "---",
        ],
    }
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_bet_history(result: SimulationResult):
    """賭け履歴を表示"""
    st.subheader("📜 賭け履歴（最新20件）")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 最新20件を取得
    recent_bets = result.bet_history[-20:][::-1]
    
    data = []
    for bet in recent_bets:
        data.append({
            "レース": f"{bet.race.track} {bet.race.race_number}R",
            "馬券種": bet.ticket.ticket_type.value,
            "馬番": str(bet.ticket.horse_numbers),
            "オッズ": f"{bet.ticket.odds:.1f}",
            "金額": f"¥{bet.ticket.amount:,}",
            "結果": "✅ 的中" if bet.is_hit else "❌ 不的中",
            "払戻": f"¥{bet.payout:,}",
            "損益": f"¥{bet.payout - bet.ticket.amount:+,}",
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)
