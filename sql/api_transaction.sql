with merger_transaction as (
select
id,
date,
account_id,
invest_account_id,
category_id,
case when type = 'expense' then amount * -1
     when type = 'income' then amount
     when type  = 'transfer' then amount * -1
     end as amount,
payee,
notes,
qty,
case when type = 'expense' then 'Expense'
     when type = 'income' then 'Income'
     when type = 'transfer' then 'TransferFrom'
     end as source
from budget.transactions
union all
select
id,
date,
to_account_id,
invest_account_id,
category_id,
to_amount as amount,
payee,
notes,
qty,
'TransferTo' as source
from budget.transactions),
merger_value as (select 
  case 
    when row_number() over (partition by b.account_id order by b.date) = 1 then TIMESTAMP '1900-01-01 00:00:00'
    else CAST(date AS TIMESTAMP)
  end as valid_from,
  case 
    when lead(date) over (partition by b.account_id order by b.date) is null then TIMESTAMP '9999-12-31 23:59:59'
    else (CAST(lead(date) over (partition by b.account_id order by b.date) AS TIMESTAMP) - INTERVAL '1 microsecond')
  end as valid_to,
  a.currency as stock_code,
  value
from budget.investment_valuations as b
inner join budget.accounts as a on a.id  =b.account_id), final as (
select
  t.date::DATE as date_sk,
  t.account_id as account_sk,
  t.invest_account_id,
  t.category_id as category_sk,
  t.amount,
  a.currency,
  t.amount * coalesce(v."value", 1) as amount_chf,
  t.payee,
  t.notes,
  t.qty as transaction_qty,
  t.source as transaction_type
from merger_transaction t
inner join budget.accounts as a on a.id = t.account_id
left join merger_value as v
  on left(v.stock_code, 3) = a.currency
  and t.date between v.valid_from::date and v.valid_to::date)

select 
    date_sk,
    account_sk,
    category_sk,
    amount as "Transaction Amount",
    amount_chf as "Transaction Amount CHF",
    payee as "Payee",
    notes as "Notes",
    transaction_qty as "Transaction Qty",
    transaction_type as "Transaction Type"
from final