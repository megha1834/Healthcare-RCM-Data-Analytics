import csv
import sqlite3
from pathlib import Path

from src.reconcile import key

DB_PATH = Path("local_output/commure.db")

def load_encounters(connection, csv_path, table_name, date_column):
    encounters = set()

    with open(csv_path, newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            encounter = key(row, date_column)

            if encounter is not None and all(encounter):
                encounters.add(encounter)

    connection.executemany(
        f"INSERT INTO {table_name} VALUES (?, ?, ?)",
        sorted(encounters)
    )

    print(f"{table_name}: {len(encounters)} unique encounters")


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("DROP TABLE IF EXISTS ehr_encounters")
        connection.execute("DROP TABLE IF EXISTS db_encounters")

        for table in ("ehr_encounters", "db_encounters"):
            connection.execute(f"""
                CREATE TABLE {table} (
                    patient_name TEXT,
                    service_date TEXT,
                    provider_name TEXT,
                    PRIMARY KEY (patient_name, service_date, provider_name)
                )
            """)

        load_encounters(
            connection, "data/EHR.csv",
            "ehr_encounters", "Date of Service"
        )

        load_encounters(
            connection, "data/DB.csv",
            "db_encounters", "from_date_range"
        )

    print("SQLite database created successfully!")


if __name__ == "__main__":
    main()