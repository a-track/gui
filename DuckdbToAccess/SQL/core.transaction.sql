select
    d.date_sk,
    t.transaction_id,
    t.date,
    t.type as transaction_type,
    t.transfer_leg,
    t.account_id,
    t.category_id,
    t.invest_account_id,
    t.amount,
    t.amount_chf,
    t.qty,
    t.payee,
    t.notes,
    t.confirmed,
    t.creation_date
from transf_transaction as t
left join core_date as d on d.date = t.date
