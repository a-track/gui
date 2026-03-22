select
  account_id,
  account_name,
  concat(account_name, ' ', account_currency) as account,
  account_type,
  company,
  account_currency,
  is_investment,
  show_in_balance,
  is_active,
  valuation_strategy
from transf_account
