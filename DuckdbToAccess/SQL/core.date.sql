select
    strftime('%Y%m%d', date)::bigint as date_sk,
    date,
    year,
    month_number,
    month_name,
    weekday,
    year_month
    from transf_date