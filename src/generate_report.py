
import sqlite3
from pathlib import Path

# ==========================================
# 1. CONNECT TO SQLITE DATABASE
# ==========================================

db_path = Path("local_output/commure.db")

if not db_path.is_file():
    raise FileNotFoundError(
        "Database not found: local_output/commure.db"
    )

connection = sqlite3.connect(db_path)


# ==========================================
# 2. EHR RECONCILIATION SUMMARY
# ==========================================

ehr_total = connection.execute("""
    SELECT COUNT(*)
    FROM ehr_encounters
""").fetchone()[0]

db_total = connection.execute("""
    SELECT COUNT(*)
    FROM db_encounters
""").fetchone()[0]

matched = connection.execute("""
    SELECT COUNT(*)
    FROM ehr_encounters AS e
    INNER JOIN db_encounters AS d
        ON e.patient_name = d.patient_name
       AND e.service_date = d.service_date
       AND e.provider_name = d.provider_name
""").fetchone()[0]

missing = ehr_total - matched

coverage = (
    round(100.0 * matched / ehr_total, 2)
    if ehr_total > 0 else 0
)


# ==========================================
# 3. NORCM CATEGORY ANALYSIS
# ==========================================

norcm_query = """
WITH categorized AS (
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
    COUNT(*) AS total,
    SUM(is_missing) AS missing,
    ROUND(
        100.0 * SUM(is_missing) / COUNT(*),
        2
    ) AS missing_rate

FROM categorized
GROUP BY category
ORDER BY category;
"""

norcm_results = connection.execute(
    norcm_query
).fetchall()


# ==========================================
# 4. MONTHLY NON-NORCM ANALYSIS
# ==========================================

monthly_query = """
WITH non_norcm AS (
    SELECT
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
    month,
    COUNT(*) AS total,
    SUM(is_missing) AS missing,
    ROUND(
        100.0 * SUM(is_missing) / COUNT(*),
        2
    ) AS missing_rate

FROM non_norcm
GROUP BY month
ORDER BY month;
"""

monthly_results = connection.execute(
    monthly_query
).fetchall()


# ==========================================
# 5. PROVIDER-LEVEL NON-NORCM ANALYSIS
# ==========================================

provider_query = """
WITH non_norcm AS (
    SELECT
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
    COUNT(*) AS total,
    SUM(is_missing) AS missing,
    ROUND(
        100.0 * SUM(is_missing) / COUNT(*),
        2
    ) AS missing_rate

FROM non_norcm
GROUP BY provider_name
ORDER BY missing DESC, provider_name;
"""

provider_results = connection.execute(
    provider_query
).fetchall()


# ==========================================
# 6. CLOSE DATABASE CONNECTION
# ==========================================

connection.close()


# ==========================================
# 7. BUILD FINAL REPORT
# ==========================================

report = """COMMURE RCM DATA RECONCILIATION REPORT
======================================

"""

report += f"Total EHR encounters: {ehr_total}\n"
report += f"Unique billing DB encounters: {db_total}\n"
report += f"Matched encounters: {matched}\n"
report += f"Missing encounters: {missing}\n"
report += f"Import coverage: {coverage}%\n"


# NORCM section

report += "\nNORCM CATEGORY ANALYSIS\n"
report += "=======================\n"

for category, total, missing_count, rate in norcm_results:
    report += (
        f"{category}: "
        f"{total} total, "
        f"{missing_count} missing, "
        f"{rate}% missing rate\n"
    )


# Monthly section

report += "\nMONTHLY NON-NORCM ANALYSIS\n"
report += "==========================\n"

for month, total, missing_count, rate in monthly_results:
    report += (
        f"{month}: "
        f"{total} total, "
        f"{missing_count} missing, "
        f"{rate}% missing rate\n"
    )


# Provider section

report += "\nPROVIDER-LEVEL NON-NORCM ANALYSIS\n"
report += "=================================\n"

for provider, total, missing_count, rate in provider_results:
    report += (
        f"{provider}: "
        f"{total} total, "
        f"{missing_count} missing, "
        f"{rate}% missing rate\n"
    )


# ==========================================
# 8. DATA VALIDATION
# ==========================================

category_total = sum(row[1] for row in norcm_results)
category_missing = sum(row[2] for row in norcm_results)

monthly_total = sum(row[1] for row in monthly_results)
monthly_missing = sum(row[2] for row in monthly_results)

provider_total = sum(row[1] for row in provider_results)
provider_missing = sum(row[2] for row in provider_results)

non_norcm_total = sum(
    row[1] for row in norcm_results
    if row[0] == "Non-NORCM"
)

non_norcm_missing = sum(
    row[2] for row in norcm_results
    if row[0] == "Non-NORCM"
)

assert category_total == ehr_total, (
    "Category totals do not match EHR total"
)

assert category_missing == missing, (
    "Category missing count does not match"
)

assert monthly_total == non_norcm_total, (
    "Monthly totals do not match Non-NORCM total"
)

assert monthly_missing == non_norcm_missing, (
    "Monthly missing count does not match"
)

assert provider_total == non_norcm_total, (
    "Provider totals do not match Non-NORCM total"
)

assert provider_missing == non_norcm_missing, (
    "Provider missing count does not match"
)

report += "\nDATA VALIDATION\n"
report += "===============\n"
report += "All reconciliation checks passed.\n"


# ==========================================
# 9. INVESTIGATION RECOMMENDATIONS
# ==========================================

report += "\nINVESTIGATION RECOMMENDATIONS\n"
report += "=============================\n"

report += (
    "1. Confirm the business meaning of NORCM "
    "and whether these encounters should be billed.\n"
)

report += (
    "2. Review import logs and code-mapping rules "
    "for missing NORCM-associated encounters.\n"
)

report += (
    "3. Investigate the 79 missing Non-NORCM encounters "
    "separately from the NORCM group.\n"
)

report += (
    "4. Review September 2024 import batches and "
    "provider-specific missing encounter patterns.\n"
)

report += (
    "5. Validate suspected discrepancies before "
    "reimporting or modifying billing records.\n"
)


# ==========================================
# 10. SAVE REPORT
# ==========================================

output_path = Path("local_output/final_report.txt")

output_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

output_path.write_text(
    report,
    encoding="utf-8"
)

print(report)

print(f"Report saved to: {output_path}")
