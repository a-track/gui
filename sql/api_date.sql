WITH date_range AS (
    SELECT 
        CAST('2020-01-01' AS DATE) AS start_date,
        CAST('2030-12-31' AS DATE) AS end_date
),
calendar AS (
    SELECT 
        unnest(generate_series(start_date, end_date, INTERVAL '1 day'))::DATE AS "Date"
    FROM date_range
)
SELECT
    "Date",
    CAST("Date" AS DATE) AS "date_sk",
    YEAR("Date") AS "Year",
    MONTH("Date") AS "Month",
    DAYNAME("Date") AS "Weekday",
    LAST_DAY("Date") AS "End of Month",
    (date_trunc('week', "Date") + INTERVAL '6 days')::DATE AS "End of Week"
FROM calendar