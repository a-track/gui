select 
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
inner join budget.accounts as a on a.id = b.account_id