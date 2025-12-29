select
  t.account_id as account_sk,
  t.category_id as category_sk,
  t.date::DATE as date_sk,
  t.amount as "Dividend Amount",
  t.amount * coalesce(er.rate, 1) as "Dividend Amount CHF",
  t.notes as "Notes",
  t.payee as "Payee"
from budget.transactions as t
left join budget.categories as c on t.category_id = c.id
left join budget.exchange_rates as er on t.date = er.date and er.currency = (select currency from budget.accounts where id = t.account_id)
where (c.category LIKE '%Dividend%' OR t.type = 'income') 
  AND t.invest_account_id IS NOT NULL