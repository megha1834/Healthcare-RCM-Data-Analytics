
import sqlite3

connection = sqlite3.connect("local_output/commure.db")

query = """
WITH non_norcm_encounters AS (

    SELECT
        e.provider_name,
        SUBSTR(e.service_date, 1, 7) AS month,

        CASE
            WHEN d.patient_name IS NULL THEN 1
            ELSE 0
        END AS is_missing

    FROM ehr_encounters AS e

    LEFT JOIN db_encounters AS d
        ON e.patient_name = d.patient_name
       AND e.service_date = d.service_date
       AND e.provider_name = d.provider_name

    WHERE NOT EXISTS (
        SELECT 1
        FROM ehr_procedures AS p
        WHERE p.patient_name = e.patient_name
          AND p.service_date = e.service_date
          AND p.provider_name = e.provider_name
          AND p.cpt_code = 'NORCM'
    )
)

SELECT
    provider_name,
    month,
    COUNT(*) AS total_encounters,
    SUM(is_missing) AS missing_encounters,

    ROUND(
        100.0 * SUM(is_missing) / COUNT(*),
        2
    ) AS missing_rate

FROM non_norcm_encounters

GROUP BY provider_name, month

HAVING SUM(is_missing) > 0

ORDER BY month, missing_encounters DESC;
"""

results = connection.execute(query).fetchall()

print("Provider | Month | Total | Missing | Rate")

for provider, month, total, missing, rate in results:
    print(f"{provider} | {month} | {total} | {missing} | {rate}%")

connection.close()
