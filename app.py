from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "MoveInSync Review Intelligence"

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

POSITIVE_TERMS = {"good", "great", "excellent", "awesome", "smooth", "easy", "helpful", "love", "best", "nice", "amazing", "convenient", "perfect", "fantastic", "satisfied"}
NEGATIVE_TERMS = {"bad", "worst", "poor", "terrible", "annoying", "useless", "hate", "crash", "error", "wrong", "failed", "failure", "slow", "stuck", "problem", "issue", "frustrating", "pathetic", "ridiculous", "not working", "doesn't work"}

RENAME_MAP = {
    "reviewId": "review_id", "score": "rating", "content": "review_text", "at": "review_date",
    "reviewCreatedVersion": "app_version", "thumbsUpCount": "helpful_votes",
    "replyContent": "developer_reply", "repliedAt": "reply_date", "userName": "author"
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={k: v for k, v in RENAME_MAP.items() if k in df.columns})
    for col in ["review_id", "author", "review_text", "app_version", "developer_reply"]:
        if col not in df.columns:
            df[col] = ""
    for col in ["rating", "helpful_votes"]:
        if col not in df.columns:
            df[col] = pd.NA
    if "review_date" not in df.columns:
        df["review_date"] = pd.NaT
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["helpful_votes"] = pd.to_numeric(df["helpful_votes"], errors="coerce").fillna(0)
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce", utc=True)
    for col in ["review_id", "author", "review_text", "app_version", "developer_reply"]:
        df[col] = df[col].fillna("").astype(str)
    df = df[df["rating"].between(1, 5, inclusive="both")].copy()
    if df["review_id"].str.strip().ne("").any():
        df = df.drop_duplicates(subset=["review_id"], keep="first")
    else:
        df = df.drop_duplicates(subset=["rating", "review_text", "review_date"], keep="first")
    return df.reset_index(drop=True)


def classify_review(text: str, rating) -> tuple[str, str, str]:
    text_l = str(text).lower()
    hits = []
    for category, patterns in CATEGORY_RULES.items():
        if any(re.search(pattern, text_l) for pattern in patterns):
            hits.append(category)
    primary = hits[0] if hits else "General / uncategorized"
    all_categories = "; ".join(hits) if hits else primary
    if not text_l.strip():
        sentiment = "No text"
    elif pd.notna(rating) and rating <= 2:
        sentiment = "Negative (rating-based)"
    elif pd.notna(rating) and rating >= 4:
        sentiment = "Positive (rating-based)"
    else:
        sentiment = "Mixed / neutral"
    return primary, all_categories, sentiment


def analyze(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    labels = out.apply(lambda r: classify_review(r["review_text"], r["rating"]), axis=1)
    out[["primary_category", "all_categories", "sentiment_signal"]] = pd.DataFrame(labels.tolist(), index=out.index)
    out["low_rating"] = out["rating"].le(2)
    out["has_text"] = out["review_text"].str.strip().ne("")
    return out


def make_report(df: pd.DataFrame, app_name: str) -> str:
    n = len(df)
    if not n:
        return "# Review Intelligence Report\n\nNo valid reviews available."
    mean_rating = df["rating"].mean()
    low_share = df["low_rating"].mean() * 100
    date_min = df["review_date"].min()
    date_max = df["review_date"].max()
    date_range = f"{date_min.date()} to {date_max.date()}" if pd.notna(date_min) and pd.notna(date_max) else "Unavailable"
    low = df[df["low_rating"]]
    themes = low["primary_category"].value_counts()
    lines = [
        f"# {app_name} — Review Intelligence Report", "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", "",
        "> **Scope note:** This report describes only the supplied review sample. It is not a representative survey of all users, and keyword-based categories are directional signals rather than confirmed root causes.", "",
        "## Executive snapshot", "",
        f"- Valid unique reviews analyzed: **{n:,}**",
        f"- Mean rating in sample: **{mean_rating:.2f}/5**",
        f"- 1–2 star reviews: **{int(df['low_rating'].sum()):,} ({low_share:.1f}%)**",
        f"- Review date coverage: **{date_range}**",
        f"- Reviews with text: **{int(df['has_text'].sum()):,} ({df['has_text'].mean()*100:.1f}%)**", "",
        "## Themes in low-rated reviews", "",
        "Counts below use the primary keyword-matched category; a review can mention multiple themes, and these labels require validation.", "",
        "| Theme | Low-rated reviews |", "|---|---:|"
    ]
    for cat, count in themes.head(10).items():
        lines.append(f"| {cat} | {int(count)} |")
    lines += ["", "## Recommended next steps", "",
              "1. Manually label a stratified sample of reviews and measure classification precision/recall before using theme counts for decisions.",
              "2. Join review themes to product telemetry, support tickets, app-version rollout dates, and booking outcomes where authorized.",
              "3. Investigate high-impact booking-state, login/crash, and tracking/ETA complaints first, but confirm severity and reproducibility with engineering data.",
              "4. Define baseline metrics before shipping fixes; evaluate post-release outcomes against comparable periods.", "",
              "## Methodology and limitations", "",
              "- Deduplicated by review ID where available and retained ratings from 1 to 5.",
              "- Categories are assigned with transparent keyword rules; they can miss synonyms and misclassify context.",
              "- Sentiment signal is based on star rating, not a model's interpretation of the text.",
              "- App-version comparisons are descriptive and do not establish causation.",
              "- Review samples can be biased by who chooses to post a review and which reviews the collection method returns.", ""]
    return "\n".join(lines)


st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")
st.title("MoveInSync Review Intelligence")
st.caption("Turn public app reviews into transparent, evidence-led product priorities.")
st.info("Prototype note: issue labels use explainable keyword rules, not validated AI classification. Treat findings as investigation leads until reviewed against telemetry and manually labeled examples.")

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader("Upload review CSV", type=["csv"])
    st.caption("Expected fields include rating, review_text, review_date, app_version, and review_id. Common Google Play Scraper field names are also supported.")
    st.divider()
    st.header("Filters")
    st.caption("Filters appear after a dataset is loaded.")

source = uploaded
if source is None:
    default_path = Path(__file__).parent / "data" / "moveinsync_reviews.csv"
    if default_path.exists():
        st.success("Using the included sample dataset. Upload another CSV in the sidebar to analyze a new collection.")
        raw_df = pd.read_csv(default_path)
    else:
        st.warning("Upload a CSV to begin.")
        st.stop()
else:
    raw_df = pd.read_csv(source)

clean = normalize_columns(raw_df)
if clean.empty:
    st.error("No valid reviews found. Check that the CSV has a rating column with values from 1 to 5.")
    st.stop()
data = analyze(clean)

with st.sidebar:
    all_versions = sorted([v for v in data["app_version"].unique() if v.strip()], reverse=True)
    versions = st.multiselect("App version", all_versions, default=all_versions)
    min_date = data["review_date"].min()
    max_date = data["review_date"].max()
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.date_input("Review date range", value=(min_date.date(), max_date.date()))
    else:
        date_range = None
    ratings = st.multiselect("Ratings", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])

filtered = data[data["rating"].isin(ratings)].copy()
if all_versions:
    filtered = filtered[filtered["app_version"].isin(versions) | filtered["app_version"].eq("")]
if date_range and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start = pd.Timestamp(date_range[0], tz="UTC")
    end = pd.Timestamp(date_range[1], tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    filtered = filtered[filtered["review_date"].isna() | filtered["review_date"].between(start, end)]

if filtered.empty:
    st.warning("No reviews match the current filters.")
    st.stop()

n = len(filtered)
low_n = int(filtered["low_rating"].sum())
mean_rating = filtered["rating"].mean()
cols = st.columns(4)
cols[0].metric("Reviews analyzed", f"{n:,}")
cols[1].metric("Mean sample rating", f"{mean_rating:.2f}/5")
cols[2].metric("1–2 star reviews", f"{low_n:,}", f"{low_n/n*100:.1f}%")
cols[3].metric("Reviews with text", f"{int(filtered['has_text'].sum()):,}")

st.subheader("Rating distribution")
rating_dist = filtered["rating"].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
st.bar_chart(rating_dist.rename_axis("Stars").to_frame("Reviews"))

left, right = st.columns(2)
with left:
    st.subheader("Issue themes in low-rated reviews")
    low = filtered[filtered["low_rating"]]
    theme_counts = low["primary_category"].value_counts().rename_axis("Theme").to_frame("Reviews")
    if theme_counts.empty:
        st.write("No low-rated reviews in the current filter.")
    else:
        st.bar_chart(theme_counts)
with right:
    st.subheader("Rating by app version")
    version_data = filtered[filtered["app_version"].str.strip().ne("")].groupby("app_version").agg(
        reviews=("rating", "size"), mean_rating=("rating", "mean"), low_star_share=("low_rating", "mean")
    ).sort_values("reviews", ascending=False).head(20)
    if version_data.empty:
        st.write("No app-version values available.")
    else:
        st.dataframe(version_data.assign(mean_rating=version_data["mean_rating"].round(2), low_star_share=(version_data["low_star_share"]*100).round(1)).rename(columns={"reviews":"Reviews", "mean_rating":"Mean rating", "low_star_share":"1–2 star (%)"}), use_container_width=True)

st.subheader("Review explorer")
search = st.text_input("Search review text", placeholder="e.g. booking, login, ETA")
category_options = sorted(filtered["primary_category"].unique())
selected_categories = st.multiselect("Primary issue category", category_options, default=category_options)
explorer = filtered[filtered["primary_category"].isin(selected_categories)].copy()
if search.strip():
    explorer = explorer[explorer["review_text"].str.contains(re.escape(search.strip()), case=False, na=False)]
show_cols = [c for c in ["review_date", "rating", "app_version", "primary_category", "all_categories", "review_text", "helpful_votes", "developer_reply"] if c in explorer.columns]
st.dataframe(explorer[show_cols].sort_values("review_date", ascending=False, na_position="last"), use_container_width=True, hide_index=True)

st.subheader("Downloads")
clean_csv = filtered.to_csv(index=False).encode("utf-8")
report_md = make_report(filtered, "MoveInSync")
c1, c2 = st.columns(2)
with c1:
    st.download_button("Download analyzed reviews (CSV)", clean_csv, file_name="moveinsync_analyzed_reviews.csv", mime="text/csv")
with c2:
    st.download_button("Download action report (Markdown)", report_md, file_name="moveinsync_review_report.md", mime="text/markdown")

with st.expander("How issue labels work"):
    st.write("The first matching category becomes the primary category. All matching categories are retained in `all_categories`. Keyword rules are transparent and easy to modify in `app.py`, but they are not a substitute for validated human or LLM classification.")
    st.code("python -m pip install -r requirements.txt\nstreamlit run app.py", language="bash")
