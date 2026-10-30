"""Encounter reconciliation; standard library only. Patient-level output stays local."""
import argparse
import csv
import json
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path


def norm(value):
    return ' '.join((value or '').strip().casefold().split())


def date_norm(value):
    return datetime.strptime(value.strip(), '%m/%d/%Y' if '/' in value else '%Y-%m-%d').date().isoformat()


def key(row, date_col):
    try:
        return (norm(row['Patient Name']), date_norm(row[date_col]), norm(row['Provider Name']))
    except (ValueError, KeyError, AttributeError):
        return None


def reconcile(ehr_path, db_path):
    ehr = defaultdict(lambda: {'codes': set(), 'rows': 0})
    db = Counter()
    invalid_ehr = invalid_db = 0
    with open(ehr_path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            k = key(row, 'Date of Service')
            if not k or not all(k):
                invalid_ehr += 1
                continue
            ehr[k]['rows'] += 1
            ehr[k]['codes'].add(norm(row.get('CPT Code', '')).upper())
    with open(db_path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            k = key(row, 'from_date_range')
            if not k or not all(k):
                invalid_db += 1
                continue
            db[k] += 1
    missing = sorted(set(ehr) - set(db))
    missing_rows = [{'Patient Name': k[0], 'Provider Name': k[2], 'date': k[1], 'ehr_codes': ','.join(sorted(ehr[k]['codes'])), 'ehr_rows': ehr[k]['rows']} for k in missing]
    norcm = {k for k in ehr if 'NORCM' in ehr[k]['codes']}
    non_norcm_missing = [k for k in missing if k not in norcm]
    provider = Counter(k[2] for k in non_norcm_missing)
    month = Counter(k[1][:7] for k in non_norcm_missing)
    cpt97035 = {k for k in ehr if '97035' in ehr[k]['codes']}
    summary = {'ehr_unique': len(ehr), 'db_rows': sum(db.values()), 'db_unique': len(db), 'matched': len(set(ehr)&set(db)), 'missing': len(missing), 'db_only': len(set(db)-set(ehr)), 'coverage_pct': round(100*len(set(ehr)&set(db))/len(ehr), 2), 'invalid_ehr_rows': invalid_ehr, 'invalid_db_rows': invalid_db, 'norcm_total': len(norcm), 'norcm_missing': len(set(missing)&norcm), 'non_norcm_missing': len(non_norcm_missing), 'non_norcm_provider_missing': dict(provider.most_common()), 'non_norcm_missing_by_month': dict(sorted(month.items())), 'non_norcm_97035_total': len(cpt97035-norcm), 'non_norcm_97035_missing': len(set(non_norcm_missing)&cpt97035)}
    return summary, missing_rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ehr', required=True)
    p.add_argument('--db', required=True)
    p.add_argument('--out', default='local_output')
    args = p.parse_args()
    summary, missing = reconcile(args.ehr, args.db)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    with (out/'missing_encounters_PRIVATE.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Patient Name','Provider Name','date','ehr_codes','ehr_rows']); writer.writeheader(); writer.writerows(missing)
    print(json.dumps(summary, indent=2))
    print('WARNING: Patient-level CSV is private. Do not upload it to GitHub.')
def parse_cpt_codes(value):
    if not value:
        return set()

    cleaned = str(value).strip().strip("{}")

    return {
        code.strip().upper()
        for code in cleaned.split(",")
        if code.strip()
    }
def group_db_cpts(rows):
    grouped = defaultdict(set)

    for row in rows:
        encounter = key(row, "from_date_range")

        if encounter is None or not all(encounter):
            continue

        codes = parse_cpt_codes(row.get("cpt_codes", ""))

        grouped[encounter].update(codes)

    return dict(grouped)


def compare_cpts(ehr_grouped, db_grouped):
    results = []

    matched_encounters = set(ehr_grouped) & set(db_grouped)

    for encounter in sorted(matched_encounters):
        ehr_codes = ehr_grouped[encounter]
        db_codes = db_grouped[encounter]

        missing = ehr_codes - db_codes
        extra = db_codes - ehr_codes

        if missing or extra:
            results.append({
                "encounter": encounter,
                "missing_cpts": sorted(missing),
                "extra_cpts": sorted(extra)
            })

    return results
from collections import defaultdict

def group_ehr_cpts(rows):
    grouped = defaultdict(set)

    for row in rows:
        encounter = key(row, "Date of Service")

        if encounter is None or not all(encounter):
          continue

        cpt = str(row.get("CPT Code", "")).strip().upper()

        if cpt:
            grouped[encounter].add(cpt)

    return dict(grouped)
if __name__ == '__main__':
    main()
