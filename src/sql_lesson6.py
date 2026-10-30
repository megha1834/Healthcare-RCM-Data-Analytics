import sqlite3

connection = sqlite3.connect("local_output/commure.db")

query = """
WITH encounter_status AS (
    SELECT
        e.patient_name,
        e.service_date,
        e.provider_name,

        CASE
            WHEN EXISTS (
                SELECT 1
                FROM ehr_procedures AS p
                WHERE p.patient_name = e.patient_name
                  AND p.service_date = e.service_date
                  AND p.provider_name = e.provider_name
                  AND p.cpt_code = 'NORCM'
            )
            THEN 'NORCM'
            ELSE 'Non-NORCM'
        END AS category,

        CASE
            WHEN d.patient_name IS NULL THEN 1
            ELSE 0
        END AS is_missing

    FROM ehr_encounters AS e

    LEFT JOIN db_encounters AS d
        ON e.patient_name = d.patient_name
       AND e.service_date = d.service_date
       AND e.provider_name = d.provider_name
)

SELECT
    category,
    COUNT(*) AS total_encounters,
    SUM(is_missing) AS missing_encounters,
    ROUND(
        100.0 * SUM(is_missing) / COUNT(*),
        2
    ) AS missing_rate

FROM encounter_status
GROUP BY category
ORDER BY missing_rate DESC;
"""

results = connection.execute(query).fetchall()

print("Category | Total | Missing | Missing Rate")

for category, total, missing, rate in results:
    print(f"{category} | {total} | {missing} | {rate}%")

connection.close()