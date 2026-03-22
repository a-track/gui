with dates as(
select valid_from as date, account_id from transf_investment
union
select
c.valid_from as date,
a.account_id
from transf_currency as c
inner join transf_account as a on a.account_currency = c.currency
union
select
date,
account_id
from
transf_transaction
),
cte as (
select
date,
account_id,
sum(amount) as amount,
sum(qty) as qty
from
transf_transaction
group by
date,
account_id
), balance as (
select
date as valid_from,
coalesce(lead(date) over (partition by account_id order by date)-1, '9999-12-31') as valid_to,
account_id,
sum(amount) over (partition by account_id order by date) as balance,
sum(qty) over (partition by account_id order by date) as balance_qty
from
cte)
select
d.date as valid_from,
coalesce(lead(d.date) over (partition by d.account_id order by d.date)-1, '9999-12-31') as valid_to,
d.account_id,
b.balance,
b.balance * coalesce(c.rate, 1) as balance_chf,
coalesce(if(a.valuation_strategy = 'Price/Qty', b.balance_qty * i.rate, i.rate), balance) as balance_value,
coalesce(if(a.valuation_strategy = 'Price/Qty', b.balance_qty * i.rate, i.rate), balance) * coalesce(c.rate, 1) as balance_value_chf,
b.balance_qty
from dates as d
inner join balance as b on b.account_id = d.account_id and d.date between b.valid_from and b.valid_to
inner join transf_account as a on a.account_id = d.account_id
left join transf_investment as i on i.account_id = d.account_id and d.date between i.valid_from and i.valid_to
left join transf_currency as c on c.currency = a.account_currency and d.date between c.valid_from and c.valid_to