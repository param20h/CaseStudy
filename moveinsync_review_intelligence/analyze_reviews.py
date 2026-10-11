"""CLI version of the review analysis; requires pandas only."""
import re
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

CATEGORY_RULES = {
    "Booking & scheduling": [r"book", r"booking", r"schedule", r"scheduled", r"waitlist", r"wait list", r"trip", r"ride cancel", r"cancelled", r"canceled", r"not booked", r"seat availability"],
    "Login & access": [r"login", r"log in", r"logged out", r"log out", r"sign in", r"otp login", r"password", r"authentication", r"session", r"access denied"],
    "Crashes & performance": [r"crash", r"freez", r"hang", r"stuck", r"slow", r"loading", r"not open", r"doesn't open", r"does not open", r"uninstall", r"reinstall", r"blank screen", r"error"],
    "Tracking & ETA": [r"gps", r"live location", r"location", r"tracking", r"track", r"eta", r"arrival time", r"pickup time", r"pick up time", r"vehicle location", r"real time", r"real-time"],
    "Routing & pickup": [r"route", r"routing", r"pickup point", r"pick-up point", r"drop point", r"detour", r"long route", r"distance", r"wrong stop", r"driver route"],
    "Notifications & communication": [r"notification", r"notify", r"alert", r"message", r"reminder", r"sms", r"push", r"email", r"not informed", r"no update"],
    "Safety & check-in": [r"safety", r"safe", r"seat belt", r"seatbelt", r"otp", r"check.?in", r"no.?show", r"driver verification", r"emergency", r"security"],
    "UI & usability": [r"ui", r"user interface", r"user experience", r"confusing", r"annoying", r"extra click", r"one more click", r"design", r"feature", r"update", r"button", r"screen", r"forced to rate", r"skip"],
    "Support & service": [r"support", r"customer care", r"helpdesk", r"help desk", r"complaint", r"no response", r"response", r"resolve", r"refund"],
}
RENAME_MAP = {"reviewId":"review_id", "score":"rating", "content":"review_text", "at":"review_date", "reviewCreatedVersion":"app_version", "thumbsUpCount":"helpful_votes", "replyContent":"developer_reply", "repliedAt":"reply_date", "userName":"author"}

def main(input_path, output_dir):
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(input_path).rename(columns=RENAME_MAP)
    for col, default in [("review_id", ""), ("review_text", ""), ("app_version", ""), ("author", ""), ("developer_reply", ""), ("rating", pd.NA), ("review_date", pd.NaT), ("helpful_votes", 0)]:
        if col not in df: df[col] = default
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df[df.rating.between(1,5)].copy()
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce", utc=True)
    df["review_text"] = df["review_text"].fillna("").astype(str)
    df["app_version"] = df["app_version"].fillna("").astype(str)
    df["review_id"] = df["review_id"].fillna("").astype(str)
    if df.review_id.str.strip().ne("").any(): df = df.drop_duplicates("review_id")
    else: df = df.drop_duplicates(["rating","review_text","review_date"])
    def classify(text, rating):
        text = text.lower(); hits=[]
        for category, patterns in CATEGORY_RULES.items():
            if any(re.search(p, text) for p in patterns): hits.append(category)
        return (hits[0] if hits else "General / uncategorized", "; ".join(hits) if hits else "General / uncategorized", "No text" if not text.strip() else ("Negative (rating-based)" if rating <= 2 else "Positive (rating-based)" if rating >= 4 else "Mixed / neutral"))
    labels = [classify(r.review_text, r.rating) for r in df.itertuples()]
    df[["primary_category","all_categories","sentiment_signal"]] = pd.DataFrame(labels,index=df.index)
    df["low_rating"] = df.rating.le(2); df["has_text"] = df.review_text.str.strip().ne("")
    csv_path = output_dir / "moveinsync_analyzed_reviews.csv"; df.to_csv(csv_path,index=False)
    low=df[df.low_rating]; themes=low.primary_category.value_counts(); n=len(df)
    dmin, dmax = df.review_date.min(), df.review_date.max()
    date_range = f"{dmin.date()} to {dmax.date()}" if pd.notna(dmin) and pd.notna(dmax) else "Unavailable"
    lines=["# MoveInSync — Review Intelligence Report","",f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}","","> **Scope:** This report describes the supplied sample only. Keyword labels are directional signals, not confirmed root causes.","","## Executive snapshot","",f"- Valid unique reviews: **{n:,}**",f"- Mean sample rating: **{df.rating.mean():.2f}/5**",f"- 1–2 star reviews: **{int(df.low_rating.sum()):,} ({df.low_rating.mean()*100:.1f}%)**",f"- Review date coverage: **{date_range}**",f"- Reviews with text: **{int(df.has_text.sum()):,} ({df.has_text.mean()*100:.1f}%)**","","## Primary keyword themes in low-rated reviews","","| Theme | Reviews |","|---|---:|"]
    lines += [f"| {cat} | {int(count)} |" for cat,count in themes.items()]
    lines += ["","## Recommended next steps","","1. Manually label a stratified sample and measure classification precision/recall.","2. Join review themes to authorized telemetry, support tickets, release dates, and booking outcomes.","3. Reproduce high-impact booking, access/reliability, and ETA/tracking reports before assigning root cause.","4. Define baseline metrics before shipping fixes and compare post-release outcomes.","","## Limitations","","- Keyword matching can miss context, synonyms, sarcasm, and non-English reviews.","- Sentiment signal is derived from star rating, not an NLP sentiment model.","- Version-level differences are descriptive and do not prove causation.","- Public review samples are self-selected and collection methods may be incomplete.",""]
    report_path=output_dir/"moveinsync_review_report.md"; report_path.write_text("\n".join(lines),encoding="utf-8")
    print(f"Rows analyzed: {n}; mean rating: {df.rating.mean():.2f}; low-star share: {df.low_rating.mean()*100:.1f}%")
    print(f"Wrote {csv_path}\nWrote {report_path}")

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("input", nargs="?", default="data/moveinsync_reviews.csv"); parser.add_argument("--output-dir", default="outputs")
    args=parser.parse_args(); main(args.input,args.output_dir)
