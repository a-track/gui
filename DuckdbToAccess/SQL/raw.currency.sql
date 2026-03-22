select
	if(date = min(date) over (partition by currency), '1900-01-01', date) as valid_from,
  coalesce(lead(date) over (partition by currency order by date) - 1, '9999-12-31') as valid_to,
	currency,
	rate
from main.exchange_rates