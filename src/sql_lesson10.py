
import sqlite3

connection = sqlite3.connect("local_output/commure.db")

query = """
WITH filtered_encounters AS (
    SELECT
        e.patient_name,
        e.service_date,
        e.provider_name,

        CASE
            WHEN d.patient_name IS NULL THEN 1
            ELSE 0
        END AS is_missing

    FROM ehr_encounters AS e

    LEFT JOIN db_encounters AS d
        ON e.patient_name = d.patient_name
       AND e.service_date = d.service_date
       AND e.provider_name = d.provider_name

    WHERE e.provider_name = 'liam young'
      AND e.service_date >= '2024-09-01'
      AND e.service_date < '2024-10-01'

      AND NOT EXISTS (
          SELECT 1
          FROM ehr_procedures AS p
          WHERE p.patient_name = e.patient_name
            AND p.service_date = e.service_date
            AND p.provider_name = e.provider_name
            AND p.cpt_code = 'NORCM'
      )
)

SELECT
    COUNT(*) AS total_encounters,
    SUM(is_missing) AS missing_encounters,
    COUNT(*) - SUM(is_missing) AS matched_encounters,

    ROUND(
        100.0 * SUM(is_missing) / COUNT(*),
        2
    ) AS missing_rate

FROM filtered_encounters;
"""

result = connection.execute(query).fetchone()

total, missing, matched, rate = result

print("Provider: Liam Young")
print("Month: September 2024")
print("Total encounters:", total)
print("Matched encounters:", matched)
print("Missing encounters:", missing)
print("Missing rate:", str(rate) + "%")

connection.close()
