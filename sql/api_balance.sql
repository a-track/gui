with cte_currency as (
  select
    date::timestamp as date,
    currency
  from budget.exchange_rates
),
cte_account as (
  select 
    id as account_id,
    currency
  from budget.accounts
  where currency <> 'CHF'
),
ranked_transactions as (
  select 
    CAST(date AS TIMESTAMP) as date,
    account_id,
    sum(amount) as daily_amount,
    sum(transaction_qty) as daily_qty,
    sum(sum(amount)) over (partition by account_id order by date) as balance_amount,
    sum(sum(transaction_qty)) over (partition by account_id order by date) as balance_qty,
    lead(CAST(date AS TIMESTAMP)) over (partition by account_id order by date) as next_date
  from api_transaction
  group by date, account_id
), transf_balance as (
select 
  date as valid_from,
  CASE
    WHEN next_date IS NULL THEN TIMESTAMP '9999-12-31 23:59:59'
    ELSE (next_date - INTERVAL '1 microsecond')
  END as valid_to,
  account_id,
  balance_amount,
  balance_qty
from ranked_transactions),
all_dates as (
  select 
    cur.date as date,
    acc.account_id
  from cte_currency as cur
  cross join cte_account as acc
  where acc.currency = cur.currency
  union
  select
    bal.valid_from::timestamp as date,
    bal.account_id as account_id
  from transf_balance as bal
  union
  select
    val.date::timestamp as date,
    account_id
  from budget.investment_valuations as val
), merger as (
select
  dat.date, 
  dat.account_id,
  bal.balance_amount,
  acc.currency,
  bal.balance_amount * coalesce(cur.rate, 1) as balance_amount_chf,
  bal.balance_qty,
  coalesce(cur.rate, 1) as currency_rate,
  coalesce(val."value", 1) as stock_price,
  coalesce(bal.balance_qty * val."value", bal.balance_amount) as balance_value,
  coalesce(bal.balance_qty * val."value", bal.balance_amount) * coalesce(cur.rate, 1) as balance_value_chf
from all_dates as dat
left join transf_balance as bal
  on bal.account_id = dat.account_id
  and dat.date between bal.valid_from::timestamp and bal.valid_to::timestamp
left join budget.accounts as acc
  on acc.id = dat.account_id
left join api_currency as cur 
  on acc.id = dat.account_id
  and cur.currency = acc.currency
  and dat.date between cur.valid_from::timestamp and cur.valid_to::timestamp
left join api_value as val
  on try_cast(left(val.stock_code, 3) as int) = dat.account_id
  and dat.date between val.valid_from::timestamp and val.valid_to::timestamp
  ), final as (
  select
  *,
  lead(CAST(date AS TIMESTAMP)) over (partition by account_id order by date) as next_date
  from merger), fact_balance as (
select 
  date as valid_from,
  case
    when next_date is null then timestamp '9999-12-31 23:59:59'
    else (next_date - interval '1 microsecond')
  end as valid_to,
  account_id,
  cast(account_id as int) as account_sk,
  balance_amount,
  currency,
  balance_amount_chf,
  balance_qty,
  currency_rate,
  stock_price,
  balance_value,
  balance_value_chf
from final
where coalesce(balance_amount, 0) <> 0)
select 
  valid_from::date as 'Valid From',
  valid_to::date as 'Valid To',
  account_sk,
  balance_amount as 'Balance Amount',
  balance_amount_chf as 'Balance Amount CHF',
  balance_qty as 'Balance Qty',
  currency_rate as 'Currency Rate',
  stock_price as 'Stock Price',
  balance_value as 'Balance Value',
  balance_value_chf as 'Balance Value CHF'
from fact_balance