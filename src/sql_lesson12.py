
import sqlite3

connection = sqlite3.connect("local_output/commure.db")

query = """
WITH missing_norcm AS (
    SELECT
        e.provider_name,
        SUBSTR(e.service_date, 1, 7) AS month

    FROM ehr_encounters AS e

    LEFT JOIN db_encounters AS d
        ON e.patient_name = d.patient_name
       AND e.service_date = d.service_date
       AND e.provider_name = d.provider_name

    WHERE d.patient_name IS NULL

    AND EXISTS (
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
    COUNT(*) AS missing_encounters

FROM missing_norcm

GROUP BY provider_name, month

ORDER BY missing_encounters DESC;
"""

results = connection.execute(query).fetchall()

print("Provider | Month | Missing NORCM Encounters")

for provider, month, missing in results:
    print(f"{provider} | {month} | {missing}")

print("Total missing NORCM encounters:", sum(row[2] for row in results))

connection.close()
