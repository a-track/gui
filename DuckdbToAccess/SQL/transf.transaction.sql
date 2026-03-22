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