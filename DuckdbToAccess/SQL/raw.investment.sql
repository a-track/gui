select
	if(date = min(date) over (partition by account_id), '1900-01-01', date) as valid_from,
  coalesce(lead(date) over (partition by account_id order by date) - 1, '9999-12-31') as valid_to,
	account_id,
	"value" as rate
from main.investment_valuations