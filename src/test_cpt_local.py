import csv

from src.reconcile import (
    group_ehr_cpts,
    group_db_cpts,
    compare_cpts
)

with open("data/EHR.csv", newline="", encoding="utf-8-sig") as f:
    ehr_rows = list(csv.DictReader(f))

with open("data/DB.csv", newline="", encoding="utf-8-sig") as f:
    db_rows = list(csv.DictReader(f))

print("EHR columns:", list(ehr_rows[0].keys()))
print("DB columns:", list(db_rows[0].keys()))

ehr_grouped = group_ehr_cpts(ehr_rows)
db_grouped = group_db_cpts(db_rows)

results = compare_cpts(ehr_grouped, db_grouped)

print("EHR unique encounters:", len(ehr_grouped))
print("DB unique encounters:", len(db_grouped))
print("Matched encounters:", len(set(ehr_grouped) & set(db_grouped)))
print("Encounters with CPT mismatches:", len(results))

print(
    "Encounters with missing CPTs:",
    sum(bool(r["missing_cpts"]) for r in results)
)

print(
    "Encounters with extra CPTs:",
    sum(bool(r["extra_cpts"]) for r in results)
)
from collections import Counter

missing_codes = Counter()
extra_codes = Counter()

for result in results:
    missing_codes.update(result["missing_cpts"])
    extra_codes.update(result["extra_cpts"])
from collections import Counter

provider_counts = Counter()
month_counts = Counter()

for result in results:

    # Check whether 97014 is an extra CPT code
    if "97014" in result["extra_cpts"]:

        # Extract encounter information
        patient, date, provider = result["encounter"]

        # Count by provider
        provider_counts[provider] += 1

        # Count by month
        month = date[:7]
        month_counts[month] += 1

print("\nExtra 97014 by provider:")
for provider, count in provider_counts.most_common():
    print(provider, count)

print("\nExtra 97014 by month:")
for month, count in sorted(month_counts.items()):
    print(month, count)

print("\nMissing CPT frequency:")
print(dict(missing_codes))

print("\nExtra CPT frequency:")
print(dict(extra_codes))
from collections import Counter

# Count all matched encounters by month
matched_by_month = Counter()

matched_keys = set(ehr_grouped) & set(db_grouped)

for encounter in matched_keys:
    patient, date, provider = encounter
    month = date[:7]
    matched_by_month[month] += 1

# Calculate extra 97014 rate for each month
print("\n97014 discrepancy rate by month:")

for month, total in sorted(matched_by_month.items()):
    affected = month_counts[month]
    rate = (affected / total) * 100

    print(
        f"{month}: {affected}/{total} "
        f"encounters ({rate:.2f}%)"
    )