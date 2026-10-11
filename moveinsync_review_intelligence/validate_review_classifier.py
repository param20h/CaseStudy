#!/usr/bin/env python3
"""Validate MoveInSync keyword theme candidates against human review annotations.

Usage:
  python3 validate_review_classifier.py \
    --annotated manual_review_sample_200_annotated.csv \
    --predictions reviews_with_theme_candidates.csv \
    --output-dir validation_outputs

The classifier is multi-label (a review can have several keyword candidates),
while the human annotation contains one primary theme. Metrics are therefore
computed as one-vs-rest per category: a category is predicted when it appears
in keyword_theme_candidates, and true when it matches human_primary_theme.
"""
import argparse
from pathlib import Path
import re
import pandas as pd

UNCAT = {"other", "other / uncategorized", "uncategorized", "general / uncategorized", "general", ""}

def norm(value):
    if pd.isna(value):
        return ""
    s = re.sub(r"\s+", " ", str(value)).strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9 /+-]", "", s)
    if s in UNCAT or "uncategorized" in s:
        return "Other / Uncategorized"
    aliases = {
        "crashes and performance": "Crashes & Performance",
        "crash and performance": "Crashes & Performance",
        "booking and scheduling": "Booking & Scheduling",
        "tracking and eta": "Tracking & ETA",
        "login and access": "Login & Access",
        "safety and checkin": "Safety & Check-in",
        "safety and check-in": "Safety & Check-in",
        "ui and usability": "UI & Usability",
        "notifications and communication": "Notifications & Communication",
        "support and service": "Support & Service",
        "routing and pickup": "Routing & Pickup",
    }
    return aliases.get(s, s.title())

def split_candidates(value):
    if pd.isna(value) or not str(value).strip():
        return set()
    return {norm(x) for x in str(value).split(";") if x.strip()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--annotated', required=True, help='CSV containing human_primary_theme and review_id')
    ap.add_argument('--predictions', required=True, help='CSV containing keyword_theme_candidates and review_id')
    ap.add_argument('--output-dir', default='validation_outputs')
    args = ap.parse_args()
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    human = pd.read_csv(args.annotated)
    pred = pd.read_csv(args.predictions)
    for col, df in [('review_id', human), ('human_primary_theme', human), ('review_id', pred), ('keyword_theme_candidates', pred)]:
        if col not in df.columns:
            raise SystemExit(f"Required column '{col}' is missing.")
    human = human[['review_id', 'human_primary_theme']].copy()
    human['human_theme_norm'] = human['human_primary_theme'].map(norm)
    pred = pred[['review_id', 'keyword_theme_candidates']].copy()
    pred['candidate_set'] = pred['keyword_theme_candidates'].map(split_candidates)
    merged = human.merge(pred, on='review_id', how='left', validate='one_to_one')
    merged['candidate_set'] = merged['candidate_set'].apply(lambda x: x if isinstance(x, set) else set())
    missing = merged['keyword_theme_candidates'].isna().sum()
    categories = sorted(set(merged['human_theme_norm']) | set().union(*merged['candidate_set'].tolist()))
    rows=[]
    for cat in categories:
        if cat == 'Other / Uncategorized':
            # Keep uncategorized in metrics, but interpret it cautiously: the human label is a catch-all.
            pass
        actual = merged['human_theme_norm'].eq(cat)
        predicted = merged['candidate_set'].apply(lambda s: cat in s)
        tp = int((actual & predicted).sum()); fp = int((~actual & predicted).sum())
        fn = int((actual & ~predicted).sum()); tn = int((~actual & ~predicted).sum())
        precision = tp/(tp+fp) if tp+fp else 0.0
        recall = tp/(tp+fn) if tp+fn else 0.0
        f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
        rows.append({'theme':cat,'human_support':int(actual.sum()),'predicted_count':int(predicted.sum()),'true_positive':tp,'false_positive':fp,'false_negative':fn,'true_negative':tn,'precision':precision,'recall':recall,'f1':f1})
    metrics=pd.DataFrame(rows).sort_values('human_support',ascending=False)
    nonzero=metrics[metrics.human_support>0]
    macro_f1=float(nonzero.f1.mean()) if len(nonzero) else 0
    total_tp=int(metrics.true_positive.sum()); total_fp=int(metrics.false_positive.sum()); total_fn=int(metrics.false_negative.sum())
    micro_p=total_tp/(total_tp+total_fp) if total_tp+total_fp else 0
    micro_r=total_tp/(total_tp+total_fn) if total_tp+total_fn else 0
    micro_f1=2*micro_p*micro_r/(micro_p+micro_r) if micro_p+micro_r else 0
    merged['candidate_contains_human_theme'] = merged.apply(lambda r: r['human_theme_norm'] in r['candidate_set'], axis=1)
    merged['candidate_list'] = merged['candidate_set'].apply(lambda s: '; '.join(sorted(s)))
    disagreements=merged.loc[~merged['candidate_contains_human_theme'], ['review_id','human_primary_theme','keyword_theme_candidates'] + ([c for c in ['rating','review_text','app_version','severity','actionability','evidence_confidence','notes'] if c in human.columns])].copy()
    # Include useful review fields from annotation file in the disagreement export.
    ann_cols=[c for c in ['review_id','rating','review_text','app_version','severity','actionability','evidence_confidence','notes'] if c in human.columns]
    if ann_cols:
        disagreements=merged.loc[~merged['candidate_contains_human_theme']].merge(human[ann_cols],on='review_id',how='left',suffixes=('','_human'))
        keep=[c for c in ['review_id','rating','review_text','app_version','human_primary_theme','keyword_theme_candidates','severity','actionability','evidence_confidence','notes'] if c in disagreements.columns]
        disagreements=disagreements[keep]
    metrics.to_csv(out/'per_theme_metrics.csv',index=False)
    disagreements.to_csv(out/'disagreements_for_review.csv',index=False)
    merged.drop(columns=['candidate_set']).to_csv(out/'matched_validation_rows.csv',index=False)
    report=[
        '# MoveInSync review classifier validation', '',
        f'- Annotated reviews matched: **{len(merged)}**',
        f'- Annotated rows without candidate predictions: **{missing}**',
        f'- Human theme appears anywhere in candidate list: **{int(merged.candidate_contains_human_theme.sum())}/{len(merged)} ({merged.candidate_contains_human_theme.mean():.1%})**',
        f'- Micro precision (one-vs-rest multi-label): **{micro_p:.3f}**',
        f'- Micro recall (one-vs-rest multi-label): **{micro_r:.3f}**',
        f'- Micro F1 (one-vs-rest multi-label): **{micro_f1:.3f}**',
        f'- Macro F1 across human-present categories: **{macro_f1:.3f}**', '',
        '## Interpretation notes',
        '- A human primary theme is compared against a multi-label candidate list. “Human theme appears in candidate list” is a useful coverage check, not exact single-label accuracy.',
        '- One-vs-rest metrics count every keyword candidate as a positive prediction; a review can therefore contribute to multiple predicted categories.',
        '- The sample was stratified and intentionally overrepresents low-rated reviews, so these results should not be treated as population-wide performance estimates.',
        '- Inspect `disagreements_for_review.csv` before changing the taxonomy or claiming classifier quality.', '',
        '## Per-theme metrics', '',
        '| Theme | Human support | Predicted | Precision | Recall | F1 |',
        '|---|---:|---:|---:|---:|---:|'
    ]
    for _,r in metrics.iterrows():
        report.append(f"| {r.theme} | {int(r.human_support)} | {int(r.predicted_count)} | {r.precision:.3f} | {r.recall:.3f} | {r.f1:.3f} |")
    (out/'validation_report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('\n'.join(report[:12]))
    print(f"\nWrote validation outputs to: {out.resolve()}")

if __name__ == '__main__': main()
