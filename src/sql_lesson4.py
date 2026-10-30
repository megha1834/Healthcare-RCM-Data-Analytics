import sqlite3

connection = sqlite3.connect("local_output/commure.db")

query = """
SELECT
    e.provider_name,
    COUNT(*) AS missing_encounters
FROM ehr_encounters AS e
LEFT JOIN db_encounters AS d
    ON e.patient_name = d.patient_name
    AND e.service_date = d.service_date
    AND e.provider_name = d.provider_name
WHERE d.patient_name IS NULL
GROUP BY e.provider_name
ORDER BY missing_encounters DESC;
"""

results = connection.execute(query).fetchall()

for provider, count in results:
    print(provider, count)

connection.close()