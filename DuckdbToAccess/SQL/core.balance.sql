select
    b.valid_from,
    b.valid_to,
    b.account_id,
    b.balance,
    b.balance_chf,
    b.balance_value,
    b.balance_value_chf,
    b.balance_qty
from transf_balance as b