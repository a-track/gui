with recursive daterange as (
    select min(date) as date
    from transf_transaction
    union all
    select date + interval '1 day'
    from daterange
    where date < (select max(date) from transf_transaction)
)
select 
    date,
    year(date) as year,
    month(date) as month_number,
    strftime('%b', date) as month_name,
    strftime('%a', date) as weekday,
    strftime('%Y%m', date) as year_month
from daterange