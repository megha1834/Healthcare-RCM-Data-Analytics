
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


# =====================================================
# 1. FILE PATHS
# =====================================================

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "local_output" / "commure.db"
OUTPUT = ROOT / "local_output" / "dashboard.png"

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Database not found: {DB_PATH}"
    )


# =====================================================
# 2. LOAD DATA FROM SQLITE
# =====================================================

connection = sqlite3.connect(DB_PATH)

# Each EHR encounter is classified as:
# NORCM or Non-NORCM.
#
# is_missing = 1 if the encounter is absent
# from the billing database.
# is_missing = 0 if the encounter is matched.

BASE_QUERY = """
WITH encounters AS (

    SELECT
        e.patient_name,
        e.service_date,
        e.provider_name,

        CASE
            WHEN d.patient_name IS NULL THEN 1
            ELSE 0
        END AS is_missing,

        CASE
            WHEN EXISTS (
                SELECT 1
                FROM ehr_procedures AS p

                WHERE p.patient_name = e.patient_name
                  AND p.service_date = e.service_date
                  AND p.provider_name = e.provider_name
                  AND UPPER(TRIM(p.cpt_code)) = 'NORCM'
            )
            THEN 'NORCM'
            ELSE 'Non-NORCM'
        END AS category

    FROM ehr_encounters AS e

    LEFT JOIN db_encounters AS d
        ON e.patient_name = d.patient_name
       AND e.service_date = d.service_date
       AND e.provider_name = d.provider_name
)
"""


# =====================================================
# 3. OVERALL KPIs
# =====================================================

summary = connection.execute(
    BASE_QUERY + """
    SELECT
        COUNT(*) AS total,
        COALESCE(SUM(is_missing), 0) AS missing
    FROM encounters
    """
).fetchone()

ehr_total = summary[0]
missing_total = summary[1]

matched_total = ehr_total - missing_total

coverage = (
    matched_total / ehr_total * 100
    if ehr_total > 0 else 0
)


# =====================================================
# 4. MONTHLY ANALYSIS — BOTH CATEGORIES
# =====================================================

monthly_rows = connection.execute(
    BASE_QUERY + """
    SELECT
        SUBSTR(service_date, 1, 7) AS month,
        category,
        COUNT(*) AS total_encounters,
        SUM(is_missing) AS missing_encounters

    FROM encounters

    GROUP BY
        SUBSTR(service_date, 1, 7),
        category

    ORDER BY month, category
    """
).fetchall()


# =====================================================
# 5. PROVIDER ANALYSIS — BOTH CATEGORIES
# =====================================================

provider_rows = connection.execute(
    BASE_QUERY + """
    SELECT
        provider_name,
        category,
        COUNT(*) AS total_encounters,
        SUM(is_missing) AS missing_encounters

    FROM encounters

    GROUP BY
        provider_name,
        category

    ORDER BY provider_name, category
    """
).fetchall()


# =====================================================
# 6. CATEGORY SUMMARY
# =====================================================

category_rows = connection.execute(
    BASE_QUERY + """
    SELECT
        category,
        COUNT(*) AS total_encounters,
        SUM(is_missing) AS missing_encounters

    FROM encounters

    GROUP BY category
    """
).fetchall()

connection.close()


# =====================================================
# 7. PREPARE MONTHLY DATA
# =====================================================

months = sorted(set(row[0] for row in monthly_rows))

monthly_data = {
    "NORCM": {},
    "Non-NORCM": {}
}

for month, category, total, missing in monthly_rows:

    monthly_data[category][month] = {
        "total": total,
        "missing": missing
    }

monthly_norcm = [
    monthly_data["NORCM"].get(
        month, {"missing": 0}
    )["missing"]
    for month in months
]

monthly_non_norcm = [
    monthly_data["Non-NORCM"].get(
        month, {"missing": 0}
    )["missing"]
    for month in months
]


# =====================================================
# 8. PREPARE PROVIDER DATA
# =====================================================

providers = sorted(
    set(row[0] for row in provider_rows)
)

provider_data = {
    provider: {
        "NORCM": {"total": 0, "missing": 0},
        "Non-NORCM": {"total": 0, "missing": 0}
    }
    for provider in providers
}

for provider, category, total, missing in provider_rows:

    provider_data[provider][category] = {
        "total": total,
        "missing": missing
    }

# Sort providers by total missing encounters
providers.sort(
    key=lambda provider: (
        provider_data[provider]["NORCM"]["missing"]
        + provider_data[provider]["Non-NORCM"]["missing"]
    ),
    reverse=True
)

provider_norcm = [
    provider_data[p]["NORCM"]["missing"]
    for p in providers
]

provider_non_norcm = [
    provider_data[p]["Non-NORCM"]["missing"]
    for p in providers
]


# =====================================================
# 9. PREPARE CATEGORY DATA
# =====================================================

category_data = {
    category: {
        "total": total,
        "missing": missing
    }
    for category, total, missing in category_rows
}

categories = ["NORCM", "Non-NORCM"]

category_missing = [
    category_data.get(
        category, {"missing": 0}
    )["missing"]
    for category in categories
]

category_rates = []

for category in categories:

    values = category_data.get(
        category,
        {"total": 0, "missing": 0}
    )

    total = values["total"]
    missing = values["missing"]

    rate = (
        missing / total * 100
        if total > 0 else 0
    )

    category_rates.append(rate)


# =====================================================
# 10. DASHBOARD DESIGN
# =====================================================

COLOR_NORCM = "#2563EB"
COLOR_NON_NORCM = "#F59E0B"

BACKGROUND = "#F3F6FB"
TEXT_COLOR = "#172554"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.titleweight": "bold"
})

fig = plt.figure(figsize=(17, 13))
fig.patch.set_facecolor(BACKGROUND)

grid = fig.add_gridspec(
    4, 2,
    height_ratios=[0.8, 2.6, 2.6, 1.4],
    hspace=0.55,
    wspace=0.38
)

fig.suptitle(
    "Healthcare RCM | Encounter Reconciliation",
    fontsize=22,
    fontweight="bold",
    color=TEXT_COLOR,
    y=0.985
)


# =====================================================
# 11. KPI CARDS
# =====================================================

kpi_grid = grid[0, :].subgridspec(
    1, 4, wspace=0.15
)

kpis = [
    ("EHR ENCOUNTERS", f"{ehr_total:,}"),
    ("MATCHED", f"{matched_total:,}"),
    ("MISSING", f"{missing_total:,}"),
    ("IMPORT COVERAGE", f"{coverage:.2f}%")
]

for i, (label, value) in enumerate(kpis):

    ax = fig.add_subplot(kpi_grid[0, i])

    ax.set_facecolor("white")

    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.text(
        0.06, 0.68,
        label,
        fontsize=10,
        color="#64748B",
        transform=ax.transAxes
    )

    ax.text(
        0.06, 0.16,
        value,
        fontsize=24,
        fontweight="bold",
        color=TEXT_COLOR,
        transform=ax.transAxes
    )


# =====================================================
# 12. PLOT 1 — MONTHLY MISSING COUNTS
# =====================================================

ax1 = fig.add_subplot(grid[1, 0])

ax1.set_facecolor("white")

x = np.arange(len(months))
width = 0.35

bars1 = ax1.bar(
    x - width / 2,
    monthly_norcm,
    width,
    label="NORCM",
    color=COLOR_NORCM
)

bars2 = ax1.bar(
    x + width / 2,
    monthly_non_norcm,
    width,
    label="Non-NORCM",
    color=COLOR_NON_NORCM
)

ax1.set_title(
    "Monthly Missing Encounters by Category"
)

ax1.set_ylabel("Missing encounters")
ax1.set_xticks(x)
ax1.set_xticklabels(months)

ax1.legend()

ax1.bar_label(
    bars1,
    padding=3,
    fontsize=9
)

ax1.bar_label(
    bars2,
    padding=3,
    fontsize=9
)

ax1.set_ylim(
    0,
    max(
        monthly_norcm + monthly_non_norcm,
        default=1
    ) * 1.22 + 1
)


# =====================================================
# 13. PLOT 2 — PROVIDER MISSING COUNTS
# =====================================================

ax2 = fig.add_subplot(grid[1, 1])

ax2.set_facecolor("white")

y = np.arange(len(providers))
height = 0.35

bars3 = ax2.barh(
    y - height / 2,
    provider_norcm,
    height,
    label="NORCM",
    color=COLOR_NORCM
)

bars4 = ax2.barh(
    y + height / 2,
    provider_non_norcm,
    height,
    label="Non-NORCM",
    color=COLOR_NON_NORCM
)

ax2.set_title(
    "Provider Missing Encounters by Category"
)

ax2.set_xlabel("Missing encounters")

ax2.set_yticks(y)

ax2.set_yticklabels([
    provider.title()
    for provider in providers
])

ax2.invert_yaxis()

ax2.legend()

ax2.bar_label(
    bars3,
    padding=3,
    fontsize=8
)

ax2.bar_label(
    bars4,
    padding=3,
    fontsize=8
)

ax2.set_xlim(
    0,
    max(
        provider_norcm + provider_non_norcm,
        default=1
    ) * 1.25 + 1
)


# =====================================================
# 14. PLOT 3 — MISSING RATE BY CATEGORY
# =====================================================

ax3 = fig.add_subplot(grid[2, 0])

ax3.set_facecolor("white")

bars5 = ax3.bar(
    categories,
    category_rates,
    color=[
        COLOR_NORCM,
        COLOR_NON_NORCM
    ],
    width=0.5
)

ax3.set_title(
    "Missing Rate Within Each Category"
)

ax3.set_ylabel("Missing rate (%)")

ax3.set_ylim(0, 115)

ax3.bar_label(
    bars5,
    fmt="%.2f%%",
    padding=5,
    fontsize=12
)


# =====================================================
# 15. PLOT 4 — SHARE OF MISSING ENCOUNTERS
# =====================================================

ax4 = fig.add_subplot(grid[2, 1])

ax4.set_facecolor("white")

if sum(category_missing) > 0:

    ax4.pie(
        category_missing,
        labels=categories,
        colors=[
            COLOR_NORCM,
            COLOR_NON_NORCM
        ],
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.78,
        wedgeprops={
            "width": 0.42,
            "edgecolor": "white"
        }
    )

ax4.set_title(
    "Share of All Missing Encounters"
)


# =====================================================
# 16. KEY FINDINGS
# =====================================================

ax5 = fig.add_subplot(grid[3, :])

ax5.set_facecolor("white")

ax5.set_xticks([])
ax5.set_yticks([])

for spine in ax5.spines.values():
    spine.set_visible(False)

norcm_missing = category_data.get(
    "NORCM", {"missing": 0}
)["missing"]

non_norcm_missing = category_data.get(
    "Non-NORCM", {"missing": 0}
)["missing"]

findings = (
    f"KEY FINDINGS\n\n"
    f"• Total missing encounters: {missing_total:,}\n"
    f"• NORCM missing: {norcm_missing:,} "
    f"({category_rates[0]:.2f}% within NORCM)\n"
    f"• Non-NORCM missing: {non_norcm_missing:,} "
    f"({category_rates[1]:.2f}% within Non-NORCM)\n\n"
    "INVESTIGATION PRIORITIES\n"
    "• Confirm whether NORCM-associated encounters should be billed.\n"
    "• Compare monthly and provider patterns in both categories.\n"
    "• Review import logs and mapping rules before concluding root cause."
)

ax5.text(
    0.025,
    0.94,
    findings,
    va="top",
    fontsize=11,
    linespacing=1.35,
    color=TEXT_COLOR,
    transform=ax5.transAxes
)


# =====================================================
# 17. SAVE DASHBOARD
# =====================================================

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

fig.savefig(
    OUTPUT,
    dpi=200,
    bbox_inches="tight",
    facecolor=fig.get_facecolor()
)

plt.close(fig)

print("\nDashboard generated successfully!")
print(f"Saved to: {OUTPUT}")

print("\nCATEGORY SUMMARY")

for category, rate in zip(
    categories,
    category_rates
):
    values = category_data.get(
        category,
        {"total": 0, "missing": 0}
    )

    print(
        f"{category}: "
        f"{values['missing']} missing / "
        f"{values['total']} total "
        f"({rate:.2f}%)"
    )
