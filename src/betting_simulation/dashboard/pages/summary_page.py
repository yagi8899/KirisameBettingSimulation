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
    st.subheader("📜 賭け履歴")
    
    if not result.bet_history:
        st.info("賭け履歴がありません")
        return
    
    # 競馬場、開催年、開催日、レース番号の昇順でソート
    sorted_bets = sorted(
        result.bet_history,
        key=lambda b: (b.race.track, b.race.year, b.race.kaisai_date, b.race.race_number)
    )
    
    # ページネーション設定
    items_per_page = st.selectbox(
        "表示件数",
        [20, 50, 100, "全件"],
        index=0,
        key="bet_history_page_size"
    )
    
    if items_per_page == "全件":
        display_bets = sorted_bets
        total_pages = 1
        current_page = 1
    else:
        total_pages = (len(sorted_bets) + items_per_page - 1) // items_per_page
        current_page = st.number_input(
            f"ページ (全{total_pages}ページ, {len(sorted_bets)}件)",
            min_value=1,
            max_value=max(1, total_pages),
            value=1,
            key="bet_history_page"
        )
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        display_bets = sorted_bets[start_idx:end_idx]
    
    data = []
    for bet in display_bets:
        # 馬名を取得
        horse_names = []
        for num in bet.ticket.horse_numbers:
            horse = bet.race.get_horse_by_number(num)
            if horse:
                horse_names.append(horse.name.strip())
            else:
                horse_names.append(f"#{num}")
        
        # 的中時のオッズを取得
        if bet.is_hit and bet.ticket.amount > 0:
            actual_odds = bet.payout / bet.ticket.amount
        else:
            actual_odds = bet.ticket.odds if bet.ticket.odds > 0 else 0
        
        # 開催日をyyyy/MM/dd形式に変換（kaisai_dateはMMDD形式）
        kaisai = bet.race.kaisai_date
        month = kaisai // 100
        day = kaisai % 100
        date_str = f"{bet.race.year}/{month:02d}/{day:02d}"
        
        data.append({
            "競馬場": bet.race.track,
            "開催日": date_str,
            "R": bet.race.race_number,
            "馬券種": bet.ticket.ticket_type.value,
            "馬番": str(bet.ticket.horse_numbers),
            "馬名": ", ".join(horse_names),
            "オッズ": f"{actual_odds:.1f}" if actual_odds > 0 else "-",
            "金額": f"¥{bet.ticket.amount:,}",
            "結果": "✅ 的中" if bet.is_hit else "❌ 不的中",
            "払戻": f"¥{bet.payout:,}",
            "損益": f"¥{bet.payout - bet.ticket.amount:+,}",
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)
