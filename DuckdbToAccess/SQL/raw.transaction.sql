select
	id as transaction_id,
	date,
	"type",
	amount,
	account_id,
	category_id,
	payee,
	notes,
	invest_account_id,
	qty,
	to_account_id,
	to_amount,
	confirmed,
	created_at::date as creation_date
  from main.transactions