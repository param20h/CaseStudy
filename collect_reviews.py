"""Collect a larger public Google Play review sample for local analysis.

Uses google-play-scraper's unofficial interface. Respect Google Play terms and
rate limits; do not treat the result as a complete or random sample.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import time
import pandas as pd
from google_play_scraper import Sort, reviews

APP_ID = "com.moveinsync.ets"
SORTS = {
    "newest": Sort.NEWEST,
    "relevant": Sort.MOST_RELEVANT,
}

def collect(count: int, lang: str, country: str, sort_name: str, pause: float) -> pd.DataFrame:
    rows = []
    token = None
    seen_tokens = set()
    while len(rows) < count:
        batch_count = min(200, count - len(rows))
        batch, next_token = reviews(
            APP_ID, lang=lang, country=country, sort=SORTS[sort_name],
            count=batch_count, continuation_token=token,
        )
        if not batch:
            print("No additional reviews returned; stopping.")
            break
        rows.extend(batch)
        print(f"Fetched {len(rows):,}/{count:,} reviews (before deduplication)")
        if not next_token or next_token in seen_tokens:
            print("Pagination ended or repeated a token; stopping.")
            break
        seen_tokens.add(next_token)
        token = next_token
        if pause:
            time.sleep(pause)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    rename = {
        "reviewId": "review_id", "userName": "author", "score": "rating",
        "content": "review_text", "at": "review_date",
        "thumbsUpCount": "helpful_votes", "reviewCreatedVersion": "app_version",
        "replyContent": "developer_reply", "repliedAt": "reply_date",
    }
    df = df.rename(columns=rename)
    for col in ["review_id", "author", "rating", "review_text", "review_date",
                "helpful_votes", "app_version", "developer_reply", "reply_date"]:
        if col not in df.columns:
            df[col] = pd.NA
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce", utc=True)
    df = df.drop_duplicates(subset=["review_id"], keep="first")
    return df[["review_id", "author", "rating", "review_text", "review_date",
               "helpful_votes", "app_version", "developer_reply", "reply_date"]]


def main():
    p = argparse.ArgumentParser(description="Collect a larger public review sample")
    p.add_argument("--count", type=int, default=5000, help="Target number of unique reviews (default: 5000)")
    p.add_argument("--lang", default="en", help="Review language code (default: en)")
    p.add_argument("--country", default="in", help="Play Store country code (default: in)")
    p.add_argument("--sort", choices=SORTS, default="newest")
    p.add_argument("--pause", type=float, default=0.5, help="Pause between pages in seconds")
    p.add_argument("--output", default="data/moveinsync_reviews_large.csv")
    p.add_argument("--append-existing", action="store_true", help="Merge with existing output file and deduplicate")
    args = p.parse_args()
    if args.count < 1:
        p.error("--count must be at least 1")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = collect(args.count, args.lang, args.country, args.sort, max(0, args.pause))
    if args.append_existing and out.exists():
        old = pd.read_csv(out)
        df = pd.concat([old, df], ignore_index=True)
        if "review_id" in df.columns:
            df = df.drop_duplicates(subset=["review_id"], keep="first")
    df.to_csv(out, index=False)
    print(f"Saved {len(df):,} unique reviews to {out}")
    if len(df):
        print(f"Date range: {df.review_date.min()} to {df.review_date.max()}")
        print("Rating distribution:")
        print(df.rating.value_counts(dropna=False).sort_index().to_string())
        print("\nCollection is self-selected and may be incomplete; document the run date and settings.")

if __name__ == "__main__":
    main()
