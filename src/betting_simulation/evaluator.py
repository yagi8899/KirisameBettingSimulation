"""的中判定

馬券の的中判定と払戻計算を行う。
"""

from betting_simulation.models import Race, Ticket, TicketType


class BetEvaluator:
    """馬券の的中判定と払戻計算"""
    
    def evaluate(self, ticket: Ticket, race: Race) -> tuple[bool, int]:
        """馬券の的中判定と払戻計算
        
        Args:
            ticket: 馬券
            race: レースデータ（結果を含む）
            
        Returns:
            (的中フラグ, 払戻金額)
        """
        if race.payouts is None:
            return False, 0
        
        match ticket.ticket_type:
            case TicketType.WIN:
                return self._evaluate_win(ticket, race)
            case TicketType.PLACE:
                return self._evaluate_place(ticket, race)
            case TicketType.QUINELLA:
                return self._evaluate_quinella(ticket, race)
            case TicketType.WIDE:
                return self._evaluate_wide(ticket, race)
            case TicketType.TRIO:
                return self._evaluate_trio(ticket, race)
            case _:
                return False, 0
    
    def _evaluate_win(self, ticket: Ticket, race: Race) -> tuple[bool, int]:
        """単勝の的中判定"""
        payouts = race.payouts
        if payouts is None:
            return False, 0
        
        horse_number = ticket.horse_numbers[0]
        
        # 1着馬と一致するか
        if horse_number == payouts.win_horse:
            # 払戻計算（馬のオッズを使用）
            horse = race.get_horse_by_number(horse_number)
            if horse:
                payout = int(ticket.amount * horse.odds)
                return True, payout
        
        return False, 0
    
    def _evaluate_place(self, ticket: Ticket, race: Race) -> tuple[bool, int]:
        """複勝の的中判定"""
        payouts = race.payouts
        if payouts is None:
            return False, 0
        
        horse_number = ticket.horse_numbers[0]
        
        # 3着以内に含まれるか
        for i, place_horse in enumerate(payouts.place_horses):
            if horse_number == place_horse:
                # 対応する払戻オッズを使用
                if i < len(payouts.place_payouts):
                    odds = payouts.place_payouts[i]
                    payout = int(ticket.amount * odds)
                    return True, payout
        
        return False, 0
    
    def _evaluate_quinella(self, ticket: Ticket, race: Race) -> tuple[bool, int]:
        """馬連の的中判定"""
        payouts = race.payouts
        if payouts is None:
            return False, 0
        
        # 馬番をソートして比較
        ticket_numbers = set(ticket.horse_numbers)
        result_numbers = set(payouts.quinella_horses)
        
        if ticket_numbers == result_numbers:
            # オッズは倍率形式（11.7 = 11.7倍）
            payout = int(ticket.amount * payouts.quinella_payout)
            return True, payout
        
        return False, 0
    
    def _evaluate_wide(self, ticket: Ticket, race: Race) -> tuple[bool, int]:
        """ワイドの的中判定"""
        payouts = race.payouts
        if payouts is None:
            return False, 0
        
        ticket_numbers = set(ticket.horse_numbers)
        
        # 3通りのワイドペアと比較
        for i, wide_pair in enumerate(payouts.wide_pairs):
            if ticket_numbers == set(wide_pair):
                if i < len(payouts.wide_payouts):
                    # オッズは倍率形式（4.2 = 4.2倍）
                    payout = int(ticket.amount * payouts.wide_payouts[i])
                    return True, payout
        
        return False, 0
    
    def _evaluate_trio(self, ticket: Ticket, race: Race) -> tuple[bool, int]:
        """三連複の的中判定"""
        payouts = race.payouts
        if payouts is None:
            return False, 0
        
        ticket_numbers = set(ticket.horse_numbers)
        result_numbers = set(payouts.trio_horses)
        
        if ticket_numbers == result_numbers:
            # オッズは倍率形式（11.5 = 11.5倍）
            payout = int(ticket.amount * payouts.trio_payout)
            return True, payout
        
        return False, 0
