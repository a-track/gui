with rates as (
  select 
    date,
    currency,
    rate
  from budget.exchange_rates
  union all
  select DISTINCT
    date,
    'CHF' as currency,
    1 as rate
  from budget.exchange_rates
),
ordered_rates as (
  select
    date,
    currency,
    rate,
    lead(date) over (partition by currency order by date) as next_date
  from rates
)
select
  date as valid_from,
  case 
    when next_date is null then date('9999-12-31')
    else (next_date - interval '1 day')
  end as valid_to,
  currency,
  rate
from ordered_rates