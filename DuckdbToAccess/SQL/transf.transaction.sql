with cte as (
select
transaction_id,
date,
-amount as amount,
account_id,
category_id,
payee,
notes,
invest_account_id,
-qty as qty,
confirmed,
creation_date,
type,
0 as transfer_leg
from
raw.transaction
where type = 'expense'
union all
select
transaction_id,
date,
amount as amount,
account_id,
category_id,
payee,
notes,
invest_account_id,
qty,
confirmed,
creation_date,
type,
0 as transfer_leg
from
raw.transaction
where type = 'income'
union all
select
transaction_id,
date,
-amount as amount,
account_id,
category_id,
payee,
notes,
invest_account_id,
-qty as qty,
confirmed,
creation_date,
'transfer_from' as type,
1 as transfer_leg
from
raw.transaction
where type = 'transfer'
union all
select
transaction_id,
date,
to_amount as amount,
to_account_id as account_id,
category_id,
payee,
notes,
invest_account_id,
qty,
confirmed,
creation_date,
'transfer_to' as type,
2 as transfer_leg
from
raw.transaction
where type = 'transfer'
)
select
cte.transaction_id,
cte.date,
cte.amount,
cte.amount * coalesce(c.rate, 1) as amount_chf,
cte.account_id,
cte.category_id,
cte.payee,
cte.notes,
cte.invest_account_id,
cte.qty,
cte.confirmed,
cte.creation_date,
cte.type,
cte.transfer_leg
from cte
left join transf_account as a on a.account_id = cte.account_id
left join transf_currency as c on c.currency = a.account_currency and cte.date between c.valid_from and c.valid_to