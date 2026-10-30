import csv
import sqlite3

from src.reconcile import key, norm

# Open our existing database
connection = sqlite3.connect("local_output/commure.db")

# Create the table if it doesn't exist
connection.execute("""
CREATE TABLE IF NOT EXISTS ehr_procedures (
    patient_name TEXT,
    service_date TEXT,
    provider_name TEXT,
    cpt_code TEXT
);
""")

# Clear old rows so rerunning doesn't create duplicates
connection.execute("DELETE FROM ehr_procedures;")

# Read EHR.csv
with open("data/EHR.csv", newline="", encoding="utf-8-sig") as file:

    reader = csv.DictReader(file)

    for row in reader:

        encounter = key(row, "Date of Service")

        if encounter is None or not all(encounter):
            continue

        patient, date, provider = encounter
        cpt = norm(row.get("CPT Code", "")).upper()

        connection.execute("""
            INSERT INTO ehr_procedures
            (patient_name, service_date, provider_name, cpt_code)
            VALUES (?, ?, ?, ?);
        """, (patient, date, provider, cpt))

connection.commit()

print("EHR procedure table created successfully!")
query = """
SELECT COUNT(*)
FROM ehr_procedures
WHERE cpt_code = 'NORCM';
"""

result = connection.execute(query).fetchone()

print("NORCM procedure rows:", result[0])
query_missing = """
SELECT COUNT(*)
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
);
"""

result = connection.execute(query_missing).fetchone()

print("Missing NORCM encounters:", result[0])
connection.close()