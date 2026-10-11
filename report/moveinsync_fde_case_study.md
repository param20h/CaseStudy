# MoveInSync Review Intelligence

## FDE Internship Case Study - Investigation Report

**Prepared:** 11 October 2026\
**Product reviewed:** MoveInSync employee transport app\
**Google Play package:** `com.moveinsync.ets`\
**Analysis dataset:** 5,000 public Google Play reviews collected with
`google-play-scraper`\
**Review period in dataset:** 22 January 2025 - 9 October 2026

------------------------------------------------------------------------

## 1. Executive summary

This investigation uses public Play Store reviews to identify
user-reported friction in the MoveInSync employee transport app, turn
those reports into investigation hypotheses, and propose a measurable
engineering response.

The collected dataset contains 5,000 unique reviews. The mean rating in
this sample is **3.77/5**, and **1,414 reviews (28.3%) are rated one or
two stars**. These figures describe the collected sample; they are not
the app's official Play Store rating and should not be interpreted as
representative of every employee using the service.

The strongest next step is not to assume that reviews prove a particular
backend defect. It is to use them as signals, prioritize workflows that
can block an employee's commute, and validate those signals against
authorized operational evidence.

**Recommended initial investigations:** 1. **Login and access
reliability** - OTP delivery/visibility, session persistence, repeated
authentication, and unexpected access failures. 2. **App stability and
performance** - launch failures, loading hangs, and errors during
time-sensitive actions. 3. **Booking and pickup workflow integrity** -
consistency between booking state, confirmation messages, and what the
user sees when reopening the app. 4. **Tracking and ETA trust** -
stale location data, ETA accuracy, and clarity when tracking is
unavailable.

These are investigation priorities derived from review evidence and
manual labels, not confirmed root causes. The first priority should be
finalized after comparing issue frequency and severity with production
telemetry, support data, and engineering effort.

## 2. Problem statement

Users rely on an employee transport app for time-sensitive tasks such as
accessing trip details, booking or changing transport, viewing OTP
information, locating pickup points, and understanding vehicle arrival.
Friction in these workflows may cause missed actions, confusion, reduced
trust, and negative app-store feedback.

The question is:

> Which recurring, actionable product problems are most likely to be
> driving dissatisfaction, what should the team investigate first, and
> how should improvement be measured?

Public reviews cannot establish the technical cause by themselves. The
analysis therefore separates: - **Observed evidence:** ratings, dates,
versions, and text in collected reviews. - **Human interpretation:**
manually assigned themes, subthemes, severity, and actionability. -
**Hypotheses:** possible technical or product explanations that require
confirmation. - **Recommendations:** proposed investigation and
measurement steps.

## 3. Dataset and methodology

### 3.1 Collection

-   5,000 unique review records were collected for package
    `com.moveinsync.ets`.
-   Collection was run on 11 October 2026; the latest review in this
    file is dated 9 October 2026.
-   The date range is 22 January 2025 through 9 October 2026.
-   The collector uses the unofficial `google-play-scraper` interface.
    Collection may be incomplete and depends on the interface and
    platform limits.
-   The reviews are self-selected public feedback, not a random sample
    of all app users.

### 3.2 Rating profile

       Rating     Reviews        Share
  ----------- ----------- ------------
       1 star       1,249        25.0%
      2 stars         165         3.3%
      3 stars         145         2.9%
      4 stars         381         7.6%
      5 stars       3,060        61.2%
    **Total**   **5,000**   **100.0%**

The one- and two-star total is 1,414 reviews (28.3%). The sample mean
rating reported by the analysis pipeline is 3.77/5. The rating
distribution is useful for describing the dataset, but it does not by
itself identify why users are dissatisfied.

### 3.3 Theme discovery and manual review

A keyword-based classifier assigned candidate themes to reviews. Initial
categories included booking and scheduling, crashes and performance,
tracking and ETA, login and access, safety and check-in, UI and
usability, routing and pickup, notifications and communication, support
and service, and other/uncategorized.

A stratified sample of 200 reviews was manually annotated. The sample
deliberately included more low-rated reviews than a simple random
sample, so its raw theme proportions must not be extrapolated to all
5,000 reviews. Manual labels are useful for reviewing taxonomy and
classifier errors, but they remain human judgments and should be checked
for consistent annotation guidance.

### 3.4 Classifier validation

The initial validation report records: - 200 annotated reviews matched
to prediction records. - Human primary theme appeared somewhere in the
candidate list for 121/200 reviews (60.5%). - Micro precision: 0.526. -
Micro recall: 0.605. - Micro F1: 0.563. - Macro F1 across human-present
categories: 0.394.

The human labels contain one primary theme per review, while the keyword
classifier can return multiple candidate themes. Therefore, "theme
appears in candidate list" is a coverage check, not exact single-label
accuracy. One-vs-rest metrics depend on the multi-label evaluation
convention. Since the rules were revised after inspecting the annotated
examples, results on this same sample are iterative development metrics,
not an independent test. Do not claim that the classifier is
production-ready.

## 4. Evidence and interpretation

### 4.1 Booking and scheduling

The original keyword pass identified booking and scheduling as the
largest specific theme among low-rated reviews. Manual examples include
complaints about scheduling friction and inconsistent booking-related
communication.

**Hypothesis to test:** the app, backend booking state, and notification
layer may not always present a consistent outcome to the user;
alternatively, some reports may reflect confusing status language or
transport-operation constraints.

**Validation:** trace a booking from submission through persistence,
response handling, UI rendering, notification delivery, and reopening
the app. Compare reported symptoms with booking success/error logs and
support tickets.

### 4.2 Login and access

In the 200-review manual sample, Login & Access was assigned as the
primary theme to 21 reviews. The baseline keyword classifier showed
relatively stronger performance for this category than for several
others (precision 0.680, recall 0.810, F1 0.739 in the supplied
validation report).

**Hypothesis to test:** OTP delivery/visibility, session expiry, token
refresh, or repeated authentication may be creating friction. The
reviews do not establish which mechanism, if any, is responsible.

**Validation:** examine authentication success rates, OTP delivery and
verification outcomes, session-expiry events, and failure rates by app
version, OS, and device model.

### 4.3 Crashes and performance

Crashes & Performance was assigned as the primary theme to 19 manually
annotated reviews. Some review language is nonspecific (for example,
"app error"), so not every item should be treated as a confirmed crash.

**Hypothesis to test:** some users experience launch failures, hangs, or
errors during important flows.

**Validation:** use crash-free session/user rate, app startup failures,
ANR/hang signals where available, API latency/error rates, and
version/device segmentation. Reproduce before assigning root cause.

### 4.4 Tracking, ETA, routing, and pickup

Reviews refer to ETA changes, tracking limitations, or pickup friction.
These reports may arise from stale GPS data, ETA prediction, routing,
driver/vehicle operations, user expectations, or unclear UI states.

**Hypothesis to test:** users may not have a sufficiently clear or
reliable view of vehicle location and arrival.

**Validation:** compare ETA predictions with actual arrival times,
inspect GPS freshness and missing-location states, and segment by route,
time window, and operational context. Do not attribute operational
delays to the app without evidence.

### 4.5 Safety and check-in; UI and usability

Some reviews criticize interaction friction around OTP access and
safety-related prompts. Safety controls should not be removed solely to
reduce clicks. The product team should determine whether the current
interaction is understandable, proportionate, accessible, and correctly
sequenced for the user's context.

**Hypothesis to test:** an interaction intended to support safety may
introduce unnecessary friction at a time-sensitive step.

**Validation:** observe representative users, measure task completion
and time-to-OTP, review accessibility, and validate safety requirements
with the product and operations owners before changing the flow.

### 4.6 Uncategorized reviews

The original low-rated keyword report contained a substantial
general/uncategorized group. This is a classification limitation, not a
product theme. It could include vague complaints, multilingual phrasing,
sarcasm, missing vocabulary, or issues outside the current taxonomy.

**Action:** inspect a random sample of uncategorized reviews, extend the
taxonomy only when repeated meaningful patterns appear, and keep an
explicit ambiguous/other route instead of forcing every review into a
specific defect category.

## 5. Recommended priority matrix

The following is a proposed investigation order. It is not a claim that
the first item has the highest measured incident rate.

  ---------------------------------------------------------------------------------------------------
  Priority       Investigation           Why it matters   First validation    Proposed owner
                                                          step                
  -------------- ----------------------- ---------------- ------------------- -----------------------
  P0             Login/access            A user blocked   Segment             Mobile +
                 reliability             from access may  authentication and  identity/backend
                                         be unable to use OTP outcomes by     
                                         core transport   version/device;     
                                         functions        reproduce failures  

  P0             App                     Failures can     Review              Mobile + platform
                 stability/performance   block            crash/ANR/startup   
                                         time-sensitive   and API error       
                                         tasks            telemetry;          
                                                          reproduce top       
                                                          signatures          

  P1             Booking-state           Confusing or     Trace booking state Booking/backend +
                 consistency             incorrect state  across backend, UI, mobile
                                         can lead users   and notifications   
                                         to believe a                         
                                         trip is not                          
                                         booked                               

  P1             ETA/tracking and pickup Incorrect or     Compare             Dispatch/operations +
                 clarity                 stale            predicted/actual    mobile
                                         information can  arrival; measure    
                                         undermine trust  GPS freshness and   
                                         and coordination missing-state       
                                                          handling            

  P2             Safety prompt and UI    Unnecessary      Usability test and  Product design +
                 friction                steps can slow   safety review of    safety/operations
                                         critical tasks,  OTP/check-in flow   
                                         but safety                           
                                         constraints must                     
                                         be preserved                         

  P2             Notifications and       Poor             Check delivery      Notifications + support
                 support loop            communication    outcomes, message   
                                         can amplify a    consistency,        
                                         defect and leave response workflows  
                                         users uncertain                      
  ---------------------------------------------------------------------------------------------------

**Decision rule:** elevate an item if production evidence shows high
frequency, high user impact, or a safety/compliance concern.
Deprioritize or reframe it if telemetry fails to corroborate the review
pattern.

## 6. Proposed 30-day plan

### Days 1-5: Confirm and baseline

-   Agree on event definitions and access to authorized telemetry.
-   Review a set of high-actionability reviews and map them to existing
    support categories.
-   Establish baselines for authentication success, crash-free sessions,
    booking success, notification consistency, and ETA error.
-   Identify app releases and device/OS segments associated with
    complaint changes.

### Days 6--10: Reproduce top failures

-   Reproduce the highest-impact authentication and stability reports.
-   Trace booking state from user action to backend persistence and
    user-visible confirmation.
-   Classify each investigated issue as reproduced, not reproduced,
    operational/process issue, UX ambiguity, or insufficient evidence.
-   Record evidence and owner for every finding.

### Days 11--20: Implement targeted fixes

-   Fix only issues supported by reproducible evidence.
-   Add regression tests for affected workflows and state transitions.
-   Improve user-facing error and stale/unavailable states where
    confusion is confirmed.
-   Use a staged rollout and documented rollback criteria.

### Days 21--30: Validate impact

-   Compare metrics with the baseline and segment by app version and
    device/OS.
-   Monitor crash, authentication, booking, and notification guardrails
    during rollout.
-   Review new low-star feedback for changes in the same themes.
-   Document outcomes, unresolved issues, and the next priority.

This is a proposed plan and depends on engineering access, team
capacity, and the availability of reliable telemetry.

## 7. Metrics and monitoring

Use operational metrics as leading indicators and app-store ratings as
lagging indicators.

  -----------------------------------------------------------------------
  Area                    Metric                  Why
  ----------------------- ----------------------- -----------------------
  Authentication          Login/OTP completion    Detects whether users
                          rate; failure rate by   can access the app
                          reason                  

  Stability               Crash-free              Detects reliability
                          sessions/users; startup regressions
                          failure rate; ANR/hang  
                          rate if available       

  Booking                 Booking                 Tests end-to-end
                          completion/success      booking integrity
                          rate; state mismatch    
                          rate; duplicate         
                          submission rate         

  Notifications           Delivery success and    Detects misleading or
                          booking-state           missing communication
                          consistency             

  Tracking                GPS freshness; ETA      Measures reliability of
                          absolute error;         location/arrival
                          proportion of           information
                          unavailable/stale       
                          states                  

  Pickup operations       Actual pickup delay and Separates app
                          missed-pickup rate,     experience from
                          segmented by route/time operational performance

  Customer feedback       Rate of 1--2 star       Monitors user feedback
                          reviews and             without treating
                          issue-specific          ratings as root-cause
                          complaints per review   proof
                          volume                  

  Support                 Contacts per 1,000      Indicates unresolved
                          trips; repeat contacts  customer friction
                          for the same issue      
  -----------------------------------------------------------------------

For each metric, define an owner, denominator, time window,
segmentation, baseline, and target before launch. Targets should be set
after baseline measurement rather than invented for the report.

## 8. Research and tools used

-   **Google Play public reviews:** primary source for user-reported
    experiences.
-   **`google-play-scraper`:** used through an unofficial interface to
    collect review records; collection may be incomplete and should be
    rerun if reproducibility is required.
-   **Python and pandas:** used to clean, inspect, aggregate, and
    compare CSV data.
-   **Explainable keyword rules:** used for initial theme candidates,
    with known limitations around context, synonyms, sarcasm, and
    multilingual text.
-   **Manual annotation:** a stratified 200-review sample was labeled
    with a primary theme, subtheme, severity, actionability, evidence
    confidence, and notes.
-   **Classifier validation exports:** used to inspect coverage,
    precision, recall, F1, and disagreements.

No internal MoveInSync telemetry, source code, support-ticket system, or
employee trip records were available in this analysis. Accordingly, the
report identifies investigation hypotheses and proposed metrics; it does
not claim to have confirmed backend root causes or measured operational
failure rates.

## 9. Limitations and responsible interpretation

1.  **Selection bias:** people who leave public reviews are not a
    representative sample of all users.
2.  **Collection limits:** the unofficial scraper may not return every
    review or all available metadata.
3.  **No causal evidence:** rating or theme differences by app version
    do not prove a release caused the issue.
4.  **Keyword limitations:** rules may miss context and may assign
    multiple themes to a single review.
5.  **Manual-label uncertainty:** labels depend on annotation guidance;
    inter-annotator agreement was not measured.
6.  **Stratified validation sample:** the 200-review sample
    overrepresents low ratings and cannot be used to estimate
    full-dataset prevalence directly.
7.  **No internal operational data:** technical causes, trip impact, and
    the financial or safety impact of individual issues remain
    unverified.

## 10. Conclusion

Public reviews provide useful signals about friction in login/access,
stability, booking, and transport visibility. The correct engineering
response is to prioritize investigation by user impact, reproduce
issues, and correlate them with authorized operational evidence before
committing to fixes.

The recommended first workstream is to validate login/access and
stability problems in parallel, while tracing booking-state consistency
as a high-impact end-to-end workflow. Tracking and ETA should be
investigated with operational arrival and GPS evidence so app defects
can be separated from transport constraints.

The review-intelligence prototype is best presented as a **directional
triage tool** that helps a team decide what to investigate. Its value is
not that it automatically discovers root causes; its value is that it
structures noisy customer feedback into testable hypotheses, links them
to operational metrics, and supports a repeatable feedback loop.

------------------------------------------------------------------------

## Suggested repository structure

``` text
moveinsync-review-intelligence/
├── README.md
├── report/
│   └── case_study.md
├── data/
│   ├── moveinsync_reviews_large.csv        # optional; consider excluding raw data from public repo
│   └── manual_review_sample_200_annotated.csv
├── src/
│   ├── collect_reviews.py
│   ├── analyze_reviews.py
│   ├── classify_reviews_v2.py
│   └── validate_review_classifier.py
├── outputs/
│   ├── moveinsync_review_report.md
│   └── validation_outputs/
└── requirements.txt
```

Before publishing, check whether the dataset contains reviewer names or
other personal data. Prefer publishing aggregated findings and a
sanitized sample rather than the full raw review export. Keep collection
run date, settings, and limitations in the README.
