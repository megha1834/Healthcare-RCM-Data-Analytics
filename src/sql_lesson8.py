
import sqlite3

# Step 1: Connect to our existing database
connection = sqlite3.connect("local_output/commure.db")

# Step 2: Write our SQL query
query = """
WITH non_norcm_encounters AS (

    SELECT
        e.service_date,

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
    SUBSTR(service_date, 1, 7) AS month,
    COUNT(*) AS total_encounters,
    SUM(is_missing) AS missing_encounters,

    ROUND(
        100.0 * SUM(is_missing) / COUNT(*),
        2
    ) AS missing_rate

FROM non_norcm_encounters

GROUP BY SUBSTR(service_date, 1, 7)

ORDER BY month;
"""

# Step 3: Execute SQL
results = connection.execute(query).fetchall()

# Step 4: Display results
print("Month | Total | Missing | Missing Rate")

for month, total, missing, rate in results:
    print(f"{month} | {total} | {missing} | {rate}%")

# Step 5: Close the connection
connection.close()
