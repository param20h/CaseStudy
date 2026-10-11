# MoveInSync Review Intelligence

**An explainable review-analysis prototype for investigating user
dissatisfaction in MoveInSync's employee transport app.**

This project collects public Google Play reviews, summarizes rating
patterns, groups review text into candidate issue themes, and supports
manual validation so teams can turn noisy feedback into testable product
and engineering hypotheses.

> **Important:** Public reviews are signals, not proof of technical root
> causes. This is an exploratory case study and review-triage
> prototype---not a production monitoring system or an official
> MoveInSync analysis.

## Contents

-   [Why this project](#why-this-project)
-   [What it does](#what-it-does)
-   [Repository structure](#repository-structure)
-   [Dataset and findings](#dataset-and-findings)
-   [Getting started](#getting-started)
-   [Run the tools](#run-the-tools)
-   [Review-analysis workflow](#review-analysis-workflow)
-   [Methodology and limitations](#methodology-and-limitations)
-   [Responsible use and data
    handling](#responsible-use-and-data-handling)
-   [Case study report](#case-study-report)

## Why this project

Employee transport apps support time-sensitive workflows such as signing
in, checking trip details, booking transport, accessing OTP information,
and tracking pickup arrangements. When those workflows are confusing or
unreliable, users may report the experience through app-store reviews.

The goal is to answer three practical questions:

1.  What problems do reviewers report most often?
2.  Which issues should a product or engineering team investigate first?
3.  How can review-derived hypotheses be checked against operational
    evidence?

The intended approach mirrors a Forward Deployed Engineer workflow:
translate customer feedback into concrete hypotheses, connect them to
product workflows, define validation steps, and recommend measurable
follow-up.

## What it does

-   **Review collection:** fetches public Google Play review records for
    the MoveInSync app using `google-play-scraper`.
-   **Rating analysis:** summarizes rating distribution, sample average
    rating, review dates, and other available fields.
-   **Theme discovery:** uses explainable keyword rules to propose
    candidate themes such as login/access, booking, crashes/performance,
    tracking/ETA, routing/pickup, safety/check-in, usability,
    notifications, and support.
-   **Interactive exploration:** provides a Streamlit dashboard for
    inspecting review-analysis results.
-   **Manual validation:** supports an annotated sample and compares
    human labels with keyword-generated theme candidates.
-   **Case-study reporting:** documents investigation hypotheses,
    proposed priorities, a 30-day plan, and metrics to validate with
    authorized operational data.

## Repository structure

``` text
moveinsync_review_intelligence/
├── .venv/                              # Local virtual environment; do not commit
├── data/
│   ├── manual_review_sample_200_annotated.csv
│   ├── moveinsync_reviews_large.csv
│   ├── moveinsync_reviews.csv
│   └── reviews_with_theme_candidates.csv
├── outputs/
│   ├── validation_outputs/
│   ├── moveinsync_analyzed_reviews.csv
│   └── moveinsync_review_report.md
├── report/
│   └── moveinsync_fde_case_study.md
├── analyze_reviews.py
├── app.py
├── collect_reviews.py
├── validate_review_classifier.py
├── requirements.txt
├── README.md
└── .gitignore
```

The exact files in `data/` and `outputs/` may change as new collection
and analysis runs are created. Keep generated outputs separate from
source code, and do not commit `.venv/`.

## Dataset and findings

The analysis dataset used for this case study contains **5,000 unique
reviews** for Google Play package `com.moveinsync.ets`, with review
dates from **22 January 2025 through 9 October 2026**. The collection
run was performed on 11 October 2026.

### Rating distribution in the collected sample

       Rating     Reviews        Share
  ----------- ----------- ------------
       1 star       1,249        25.0%
      2 stars         165         3.3%
      3 stars         145         2.9%
      4 stars         381         7.6%
      5 stars       3,060        61.2%
    **Total**   **5,000**   **100.0%**

The analysis report records a sample mean rating of **3.77/5** and
**1,414 one- or two-star reviews (28.3%)**.

These are statistics for the collected sample---not the official current
Play Store rating and not necessarily representative of all app users.

### Investigation areas

The review analysis suggests investigating:

-   **Login and access:** OTP, session, and authentication friction.
-   **App stability and performance:** launch failures, hangs, and
    errors.
-   **Booking and scheduling:** booking-state clarity and consistency
    between the app and notifications.
-   **Tracking and ETA:** stale location information, arrival estimates,
    and tracking availability.
-   **Routing, pickup, safety/check-in, usability, notifications, and
    support:** investigate recurring reports and validate their
    operational impact.

These are review-derived hypotheses. Confirm root causes using
authorized telemetry, support records, reproduction steps, and release
history before recommending or shipping fixes.

## Getting started

### Requirements

-   Python 3
-   `pip`
-   A terminal
-   Internet access for collecting public reviews
-   Dependencies listed in `requirements.txt`

The project has been used with Python 3.14, but compatibility depends on
the installed package versions.

### 1. Open the project directory

Run commands from the directory containing `analyze_reviews.py`,
`app.py`, and `requirements.txt`.

``` bash
cd moveinsync_review_intelligence
```

### 2. Activate or create a virtual environment

If `.venv/` already exists:

**macOS / Linux**

``` bash
source .venv/bin/activate
```

**Windows PowerShell**

``` powershell
.venv\Scripts\Activate.ps1
```

To create a new environment:

``` bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Windows, use `python` instead of `python3` if needed.

## Run the tools

### A. Collect a larger review sample

``` bash
python3 collect_reviews.py --count 5000 --lang en --country in --sort newest
```

The collector is configured to write the large dataset to:

``` text
data/moveinsync_reviews_large.csv
```

Collection can return fewer records than requested because of platform
or scraper limitations. Record the run date and settings for each
collection.

### B. Analyze the collected reviews

``` bash
python3 analyze_reviews.py data/moveinsync_reviews_large.csv --output-dir outputs_large
```

Inspect `outputs_large/` after the run. To analyze the smaller dataset:

``` bash
python3 analyze_reviews.py data/moveinsync_reviews.csv --output-dir outputs
```

### C. Launch the dashboard

``` bash
streamlit run app.py
```

Streamlit prints a local URL in the terminal. Open it in your browser.
If you change dataset paths, verify that the dashboard reads the
intended file.

### D. Validate the classifier

Example command:

``` bash
python3 validate_review_classifier.py \
  --annotated data/manual_review_sample_200_annotated.csv \
  --predictions data/reviews_with_theme_candidates.csv \
  --output-dir outputs/validation_outputs
```

Ensure the annotation and prediction files exist at those paths and
share a stable review identifier. Check the script's actual command-line
options with:

``` bash
python3 validate_review_classifier.py --help
```

## Review-analysis workflow

1.  **Collect:** retrieve a review sample and record collection
    settings.
2.  **Inspect:** check duplicate IDs, date coverage, missing fields,
    language, and rating distribution.
3.  **Generate candidates:** run the keyword-based analysis and inspect
    the report.
4.  **Annotate:** manually label a stratified sample using a documented
    taxonomy and consistent scoring guidance.
5.  **Validate:** compare candidate themes with manual labels and
    inspect false positives and missed themes.
6.  **Prioritize:** rank investigation areas by user impact, evidence
    strength, frequency, and feasibility---not keyword count alone.
7.  **Verify:** compare hypotheses with authorized telemetry, support
    records, release history, and operational outcomes.
8.  **Monitor:** define baselines and owners, ship changes cautiously,
    and check whether relevant outcomes improve.

## Methodology and limitations

-   **Self-selection bias:** people who post reviews are not a random
    sample of all employees or app users.
-   **Collection limits:** `google-play-scraper` is an unofficial
    interface and may not return every review or available field.
-   **Keyword classification:** rules can miss synonyms, context,
    sarcasm, multilingual text, and multiple issues in one review.
-   **Manual-label uncertainty:** human annotation can be inconsistent;
    document guidance and inter-annotator agreement if multiple
    reviewers are involved.
-   **Stratified validation:** the 200-review sample intentionally
    overrepresents low ratings. Its raw theme proportions should not be
    treated as population estimates.
-   **Iterative evaluation:** if classifier rules are changed after
    inspecting the annotated sample, results on that same sample are
    development metrics, not an independent test.
-   **No confirmed root causes:** public reviews alone cannot prove that
    a backend service, app release, GPS system, notification service, or
    transport operation caused a complaint.
-   **No internal telemetry:** this case study does not include
    MoveInSync internal source code, production logs, employee trip
    records, or support-ticket data.

## Responsible use and data handling

Before publishing this repository:

-   Review raw CSV files for reviewer names, review IDs, or other fields
    that should not be shared unnecessarily.
-   Prefer aggregated findings and a sanitized sample over the full raw
    review export.
-   Do not include credentials, access tokens, private logs, or internal
    company data.
-   Respect applicable platform terms and collection limits.
-   Label metrics as sample-specific and retain the run date and
    collection settings.
-   Do not present review text as proof of a technical defect or use it
    to identify individual reviewers.

## Case study report

The detailed report is available at
[`report/moveinsync_fde_case_study.md`](report/moveinsync_fde_case_study.md).
It covers the problem statement, dataset, methodology, findings,
investigation priorities, a proposed 30-day plan, metrics, tools, and
limitations.

## Future improvements

-   Add a more nuanced taxonomy and phrase-level evidence for each
    predicted theme.
-   Evaluate on a new, independently annotated sample.
-   Add confidence and an explicit ambiguous/needs-review outcome.
-   Track theme frequency over time and by app version without claiming
    causation.
-   Connect themes to authorized support and operational data where
    access is approved.
-   Add tests for data cleaning, classification rules, and report
    generation.
-   Provide a reproducible run configuration and a compact, sanitized
    demo dataset.

------------------------------------------------------------------------

**Built as an exploratory FDE case study:** using customer feedback to
identify testable hypotheses, connect them to operational workflows, and
recommend measurable next steps.
