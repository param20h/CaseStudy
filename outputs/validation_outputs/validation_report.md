# MoveInSync review classifier validation

- Annotated reviews matched: **200**
- Annotated rows without candidate predictions: **0**
- Human theme appears anywhere in candidate list: **121/200 (60.5%)**
- Micro precision (one-vs-rest multi-label): **0.526**
- Micro recall (one-vs-rest multi-label): **0.605**
- Micro F1 (one-vs-rest multi-label): **0.563**
- Macro F1 across human-present categories: **0.394**

## Interpretation notes
- A human primary theme is compared against a multi-label candidate list. “Human theme appears in candidate list” is a useful coverage check, not exact single-label accuracy.
- One-vs-rest metrics count every keyword candidate as a positive prediction; a review can therefore contribute to multiple predicted categories.
- The sample was stratified and intentionally overrepresents low-rated reviews, so these results should not be treated as population-wide performance estimates.
- Inspect `disagreements_for_review.csv` before changing the taxonomy or claiming classifier quality.

## Per-theme metrics

| Theme | Human support | Predicted | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Other / Uncategorized | 83 | 127 | 0.606 | 0.928 | 0.733 |
| Login & Access | 21 | 25 | 0.680 | 0.810 | 0.739 |
| UI & Usability | 21 | 12 | 0.250 | 0.143 | 0.182 |
| Crashes & Performance | 19 | 12 | 0.583 | 0.368 | 0.452 |
| Routing & Pickup | 15 | 8 | 0.250 | 0.133 | 0.174 |
| Booking & Scheduling | 11 | 17 | 0.294 | 0.455 | 0.357 |
| Tracking & ETA | 11 | 11 | 0.455 | 0.455 | 0.455 |
| Support & Service | 8 | 5 | 0.400 | 0.250 | 0.308 |
| Safety & Check-in | 6 | 7 | 0.000 | 0.000 | 0.000 |
| Notifications & Communication | 5 | 6 | 0.500 | 0.600 | 0.545 |
