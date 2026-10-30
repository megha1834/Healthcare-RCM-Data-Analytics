
import sqlite3

# Connect to our existing database
connection = sqlite3.connect("local_output/commure.db")

# Choose which provider and month to investigate
provider = "liam young"
start_date = "2024-09-01"
end_date = "2024-10-01"

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

    WHERE e.provider_name = ?
      AND e.service_date >= ?
      AND e.service_date < ?

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
    COUNT(*) AS total,
    COALESCE(SUM(is_missing), 0) AS missing

FROM filtered_encounters;
"""

# Pass our chosen values into the query
result = connection.execute(
    query,
    (provider, start_date, end_date)
).fetchone()

total, missing = result

rate = round(100 * missing / total, 2) if total else 0

print("Provider:", provider)
print("Date range:", start_date, "to", end_date, "(exclusive)")
print("Total encounters:", total)
print("Matched encounters:", total - missing)
print("Missing encounters:", missing)
print("Missing rate:", str(rate) + "%")

connection.close()
