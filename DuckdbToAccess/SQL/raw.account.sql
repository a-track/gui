select
	id as account_id,
	account as account_name,
	"type" as account_type,
	company as company,
	currency as account_currency,
	is_investment as is_investment,
	show_in_balance as show_in_balance,
	is_active as is_active,
	valuation_strategy as valuation_strategy
from main.accounts