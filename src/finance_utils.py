from datetime import date
import math

def xirr(transactions):
    """
    Calculate the Extended Internal Rate of Return.
    transactions: list of (date, amount) tuples.
                  Amounts: Negative for investment, Positive for return.
    Returns: float (0.10 = 10%) or None if didn't converge.
    """
    if not transactions or len(transactions) < 2:
        return None
    
    amounts = [t[1] for t in transactions]
    if all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts):
        return 0.0

    transactions.sort(key=lambda x: x[0])
    
    start_date = transactions[0][0]
    
    def xnpv(rate, trans):
        val = 0.0
        for d, amt in trans:
            days = (d - start_date).days
            val += amt / pow(1.0 + rate, days / 365.0)
        return val

    def xnpv_deriv(rate, trans):
        val = 0.0
        for d, amt in trans:
            days = (d - start_date).days
            if days == 0:
                continue
            term = days / 365.0
            val -= term * amt / pow(1.0 + rate, term + 1.0)
        return val

    try:
        rate = 0.1 
        for _ in range(50):
            f = xnpv(rate, transactions)
            df = xnpv_deriv(rate, transactions)
            if df == 0:
                break
            new_rate = rate - f / df
            if abs(new_rate - rate) < 1e-6:
                return new_rate
            rate = new_rate
    except:
        return None
        
    return None

def calculate_linked_twr(valuations, cashflows):
    """
    Calculate Time-Weighted Return using Linked Modified Dietz.
    valuations: list of (date, value) sorted by date.
    cashflows: list of (date, amount) sorted by date.
               Method assumes Flow values are:
               +External Inflow (Deposit)
               -External Outflow (Withdrawal) 
               (Note: This is opposite of XIRR convention usually, but let's standardize)
               
    Standardization for this function:
    - Flows: Positive = Money Added to Portfolio implies we subtract from End Val to isolate return.
    - Flows: Negative = Money Removed implies we add back to End Val.
    
    BUT `get_account_cash_flows` returns:
    - Deposit (In) = Negative
    - Withdrawal (Out) = Positive
    (Matches XIRR: -Inv, +Ret)
    
    So for TWR:
    - Deposit (Neg in XIRR list) -> is a Contribution. 
    - Withdrawal (Pos in XIRR list) -> is a Distribution.
    
    Modified Dietz Formula for Period:
    R = (CurrentVal - StartVal - NetContrib) / (StartVal + WeightedNetContrib)
    
    Where NetContrib = Sum(Deposits) - Sum(Withdrawals)
    Use XIRR flows: NetContrib = -Sum(Flows)  (since Dep is neg)
    
    """
    if not valuations or len(valuations) < 2:
        return None

    twr = 1.0
    
    for i in range(len(valuations) - 1):
        start_date, start_val = valuations[i]
        end_date, end_val = valuations[i+1]

        
        period_flows = [f for f in cashflows if start_date < f[0] <= end_date]
        
        net_contrib = 0.0
        weighted_contrib = 0.0
        
        period_len = (end_date - start_date).days
        if period_len == 0:
            continue
            
        for d, amt in period_flows:
            contribution = -amt 
            
            net_contrib += contribution
            
            days_in = (end_date - d).days
            weight = days_in / period_len
            weighted_contrib += contribution * weight
            
        numerator = end_val - start_val - net_contrib
        denominator = start_val + weighted_contrib
        
        if denominator == 0:
            period_return = 0.0
        else:
            period_return = numerator / denominator
            
        twr *= (1.0 + period_return)
        
    return (twr - 1.0) * 100.0
