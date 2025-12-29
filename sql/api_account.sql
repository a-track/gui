select
id as account_sk,
id as 'Account Nr',
account as 'Account Name',
type as 'Account Type',
company as 'Company',
currency as 'Account Currency',
is_investment as 'Is Investment'
from budget.accounts