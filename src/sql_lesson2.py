import sqlite3

connection = sqlite3.connect("local_output/commure.db")

query = """
SELECT COUNT(*)
FROM ehr_encounters AS e
LEFT JOIN db_encounters AS d
    ON e.patient_name = d.patient_name
    AND e.service_date = d.service_date
    AND e.provider_name = d.provider_name
WHERE d.patient_name IS NULL;
"""

result = connection.execute(query).fetchone()

print("Missing encounters:", result[0])

connection.close()