# RCM Operations Case Study — Encounter Reconciliation

Problem 2: Compare EHR and billing database records by **patient name + date of service + rendering provider**, rather than raw procedure-row counts. The EHR can have multiple CPT rows per encounter.

## Run

Requires Python 3.10+ (standard library only):

```bash
python -m src.reconcile --ehr "path/to/EHR.csv" --db "path/to/DB.csv" --out local_output
python -m unittest discover -s tests -v
```

`local_output/summary.json` contains aggregate results. `local_output/missing_encounters_PRIVATE.csv` contains patient names and **must never be committed to a public repository**. Original datasets are also excluded.

## Method

Normalize names and providers (trim, casefold, collapse whitespace); standardize dates to ISO; deduplicate by encounter key; perform EHR minus DB set difference. CPT codes are used for subgroup analysis, not for the encounter matching key.

## Interpretation

The `NORCM` and CPT 97035 associations are **hypotheses**, not confirmed root causes. Validate against eligibility/business rules, import logs, and mapping history. Confirm name-based key limitations (name changes, duplicates, inconsistent identifiers) before production use.
