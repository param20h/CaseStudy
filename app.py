from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "MoveInSync Review Intelligence"

CATEGORY_RULES = {
    "Booking & Scheduling": [r"\bbook(?:ing|ed)?\b", r"\bschedul(?:e|ed|ing)\b", r"wait.?list", r"\btrip\b", r"ride cancel", r"cancelled", r"canceled", r"not booked", r"seat availability"],
    "Login & Access": [r"\blog.?in\b", r"\bsign.?in\b", r"logged out", r"\botp\b", r"password", r"authentication", r"\bsession\b", r"access denied"],
    "Crashes & Performance": [r"\bcrash(?:es|ed)?\b", r"freez", r"\bhang(?:s|ing)?\b", r"\bstuck\b", r"\bslow\b", r"loading", r"not open", r"does not open", r"doesn't open", r"uninstall", r"reinstall", r"blank screen", r"\berror\b"],
    "Tracking & ETA": [r"\bgps\b", r"live location", r"\blocation\b", r"\btracking\b", r"\btrack\b", r"\beta\b", r"arrival time", r"pickup time", r"pick.?up time", r"vehicle location", r"real.?time"],
    "Routing & Pickup": [r"\broute\b", r"\brouting\b", r"pickup point", r"pick.?up point", r"drop point", r"\bdetour\b", r"long route", r"\bdistance\b", r"wrong stop", r"driver route"],
    "Notifications & Communication": [r"\bnotification", r"\bnotify\b", r"\balert\b", r"\bmessage\b", r"\breminder\b", r"\bsms\b", r"\bpush\b", r"\bemail\b", r"not informed", r"no update"],
    "Safety & Check-in": [r"\bsafety\b", r"\bsafe\b", r"seat.?belt", r"check.?in", r"no.?show", r"driver verification", r"\bemergency\b", r"\bsecurity\b"],
    "UI & Usability": [r"\bui\b", r"user interface", r"user experience", r"\bconfusing\b", r"\bannoying\b", r"extra click", r"one more click", r"\bdesign\b", r"\bfeature\b", r"\bupdate\b", r"\bbutton\b", r"\bscreen\b", r"forced to rate", r"\bskip\b"],
    "Support & Service": [r"\bsupport\b", r"customer care", r"help.?desk", r"\bcomplaint\b", r"no response", r"\bresponse\b", r"\bresolve\b", r"\brefund\b"],
}

RENAME_MAP = {
    "reviewId": "review_id", "score": "rating", "content": "review_text",
    "at": "review_date", "reviewCreatedVersion": "app_version",
    "thumbsUpCount": "helpful_votes", "replyContent": "developer_reply",
    "repliedAt": "reply_date", "userName": "author",
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
    # Accept ISO timestamps, Unix seconds, and Unix milliseconds.
    raw_dates = df["review_date"]
    numeric_dates = pd.to_numeric(raw_dates, errors="coerce")
    parsed_dates = pd.to_datetime(raw_dates, errors="coerce", utc=True)
    seconds_mask = numeric_dates.between(1_000_000_000, 9_999_999_999)
    millis_mask = numeric_dates.between(1_000_000_000_000, 9_999_999_999_999)
    if seconds_mask.any():
        parsed_dates.loc[seconds_mask] = pd.to_datetime(numeric_dates.loc[seconds_mask], unit="s", errors="coerce", utc=True)
    if millis_mask.any():
        parsed_dates.loc[millis_mask] = pd.to_datetime(numeric_dates.loc[millis_mask], unit="ms", errors="coerce", utc=True)
    df["review_date"] = parsed_dates
    for col in ["review_id", "author", "review_text", "app_version", "developer_reply"]:
        df[col] = df[col].fillna("").astype(str).replace({"nan": "", "None": ""})
    df = df[df["rating"].between(1, 5, inclusive="both")].copy()
    if df["review_id"].str.strip().ne("").any():
        with_id = df["review_id"].str.strip().ne("")
        identified = df[with_id].drop_duplicates(subset=["review_id"], keep="first")
        unidentified = df[~with_id].drop_duplicates(subset=["rating", "review_text", "review_date"], keep="first")
        df = pd.concat([identified, unidentified], ignore_index=True)
    else:
        df = df.drop_duplicates(subset=["rating", "review_text", "review_date"], keep="first")
    return df.reset_index(drop=True)


def classify_review(text: str) -> tuple[str, str]:
    text_l = str(text).lower()
    hits = [category for category, patterns in CATEGORY_RULES.items()
            if any(re.search(pattern, text_l) for pattern in patterns)]
    primary = hits[0] if hits else "General / Uncategorized"
    return primary, "; ".join(hits) if hits else primary


def analyze(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    labels = out["review_text"].apply(classify_review)
    out["primary_category"] = labels.apply(lambda x: x[0])
    out["all_categories"] = labels.apply(lambda x: x[1])
    out["low_rating"] = out["rating"].le(2)
    out["has_text"] = out["review_text"].str.strip().ne("")
    out["month"] = out["review_date"].dt.to_period("M").astype("string")
    return out


def date_coverage(df: pd.DataFrame) -> str:
    dates = df["review_date"].dropna()
    if dates.empty:
        return "Date coverage unavailable"
    return f"{dates.min():%d %b %Y} – {dates.max():%d %b %Y}"


def make_report(df: pd.DataFrame) -> str:
    if df.empty:
        return "# MoveInSync Review Intelligence\n\nNo reviews match the current filters."
    low = df[df["low_rating"]]
    themes = theme_counts(low)
    date_text = date_coverage(df)
    lines = [
        "# MoveInSync Review Intelligence Report", "",
        f"Generated: {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}", "",
        "> Scope: This report describes the supplied public-review sample only. It is not representative of all users. Keyword-based labels are directional signals, not confirmed root causes.", "",
        "## Snapshot", "",
        f"- Reviews analyzed: **{len(df):,}**",
        f"- Mean sample rating: **{df['rating'].mean():.2f}/5**",
        f"- 1–2 star reviews: **{int(df['low_rating'].sum()):,} ({df['low_rating'].mean()*100:.1f}%)**",
        f"- Reviews containing text: **{int(df['has_text'].sum()):,} ({df['has_text'].mean()*100:.1f}%)**",
        f"- Date coverage: **{date_text}**", "",
        "## Keyword theme matches in 1–2 star reviews", "",
        "A single review can match more than one theme; these are exploratory counts.", "",
        "| Theme | Reviews |", "|---|---:|",
    ]
    for theme, count in themes.items():
        lines.append(f"| {theme} | {count} |")
    lines += ["", "## Recommended next steps", "",
              "1. Manually review a stratified sample and evaluate theme precision and recall.",
              "2. Join themes with authorized crash, login, booking, GPS/ETA, support, and release telemetry.",
              "3. Reproduce high-impact reports before assigning root cause.",
              "4. Establish baselines and compare outcomes after any product change.", "",
              "## Limitations", "",
              "- Reviews are self-selected and may not represent the full user population.",
              "- Keyword rules can miss synonyms and misunderstand context.",
              "- Version-level differences are descriptive and do not establish causality.",
              "- Rating-based low-rating status is not the same as text sentiment.", ""]
    return "\n".join(lines)


def theme_counts(df: pd.DataFrame) -> pd.Series:
    """Count each matching theme once per review, including secondary matches."""
    counts = {}
    for _, row in df.iterrows():
        categories = [c.strip() for c in str(row.get("all_categories", "")).split(";") if c.strip()]
        for category in set(categories):
            if category != "General / Uncategorized":
                counts[category] = counts.get(category, 0) + 1
    return pd.Series(counts, dtype="int64").sort_values(ascending=False)


def style_app() -> None:
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .stApp { background: #f7f9fc; color: #17233d; }
      [data-testid="stHeader"] { background: rgba(247,249,252,.92); }
      [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e5eaf2; }
      .block-container { max-width: 1600px; padding-top: 1.5rem; padding-bottom: 2.5rem; }
      h1, h2, h3 { font-family: 'Manrope', sans-serif !important; letter-spacing: -.035em; color: #17233d; }
      h1 { font-size: clamp(1.8rem, 2.6vw, 2.7rem) !important; font-weight: 800 !important; }
      h2 { font-size: 1.35rem !important; font-weight: 750 !important; }
      h3 { font-size: 1.05rem !important; font-weight: 700 !important; }
      [data-testid="stMetric"] { background: #fff; border: 1px solid #e5eaf2; border-radius: 15px; padding: 17px 18px; box-shadow: 0 2px 8px rgba(25,45,80,.025); }
      [data-testid="stMetricLabel"] { color: #64748b; font-size: .85rem; }
      [data-testid="stMetricValue"] { color: #17233d; font-family: 'Manrope', sans-serif; font-weight: 800; }
      [data-testid="stVerticalBlockBorderWrapper"] { background: #fff; border-color: #e5eaf2 !important; border-radius: 16px; }
      div[data-testid="stAlert"] { border-radius: 12px; }
      .eyebrow { text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; font-weight: 700; color: #64748b; }
      .subtle { color: #64748b; font-size: .88rem; }
      .priority-card { background: white; border: 1px solid #e7ebf3; border-radius: 13px; padding: 14px; min-height: 142px; }
      .priority-rank { color: #e04f5f; font-weight: 800; font-size: .76rem; letter-spacing: .06em; }
      .priority-title { color: #17233d; font-weight: 750; margin: 6px 0 4px; }
      .priority-meta { color: #64748b; font-size: .82rem; }
      .priority-tag { display: inline-block; border-radius: 6px; padding: 3px 7px; font-size: .72rem; font-weight: 700; margin-top: 9px; background: #fff1f2; color: #be3345; }
      .stDownloadButton button, .stButton button { border-radius: 10px; font-weight: 650; }
      hr { border-color: #e5eaf2; }
    </style>
    """, unsafe_allow_html=True)


st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide", initial_sidebar_state="expanded")
style_app()

with st.sidebar:
    st.markdown("## MoveInSync")
    st.caption("Review Intelligence")
    st.markdown("---")
    st.markdown("### Data source")
    uploaded = st.file_uploader("Upload Google Play review CSV", type=["csv"], help="Accepts common Google Play Scraper column names.")
    st.caption("Expected fields: rating, review text, review date, app version. Review IDs are used for deduplication when available.")
    st.markdown("---")
    st.markdown("### Filters")
    if st.button("Reset filters", use_container_width=True):
        for key in ["filter_ratings", "filter_versions", "filter_themes", "filter_dates", "review_search"]:
            st.session_state.pop(key, None)
        st.rerun()

source = uploaded
if source is None:
    default_path = Path(__file__).parent / "data" / "moveinsync_reviews_large.csv"
    if not default_path.exists():
        default_path = Path(__file__).parent / "data" / "moveinsync_reviews.csv"
    if default_path.exists():
        try:
            raw_df = pd.read_csv(default_path)
            st.sidebar.success(f"Loaded {default_path.name}")
        except Exception as exc:
            st.error(f"Could not read the default CSV: {exc}")
            st.stop()
    else:
        st.title(APP_TITLE)
        st.info("Upload a review CSV in the sidebar to begin.")
        st.stop()
else:
    try:
        raw_df = pd.read_csv(source)
    except Exception as exc:
        st.error(f"Could not read the uploaded CSV: {exc}")
        st.stop()

try:
    clean = normalize_columns(raw_df)
except Exception as exc:
    st.error(f"Could not normalize the CSV. Check its column names and data types. Details: {exc}")
    st.stop()

if clean.empty:
    st.error("No valid reviews found. The CSV must contain a rating/score column with values from 1 to 5.")
    st.stop()

data = analyze(clean)
valid_dates = data["review_date"].dropna()
all_versions = sorted([v for v in data["app_version"].unique() if v.strip()], reverse=True)
all_themes = sorted({cat for values in data["all_categories"] for cat in str(values).split(";") if cat.strip()})
if "General / Uncategorized" in all_themes:
    all_themes.remove("General / Uncategorized")
all_themes.append("General / Uncategorized")

with st.sidebar:
    selected_ratings = st.multiselect("Ratings", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5], key="filter_ratings")
    selected_versions = st.multiselect("App versions", all_versions, default=all_versions, key="filter_versions")
    selected_themes = st.multiselect("Issue themes", all_themes, default=all_themes, key="filter_themes")
    if not valid_dates.empty:
        min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
        date_value = st.session_state.get("filter_dates", (min_date, max_date))
        if isinstance(date_value, (tuple, list)) and len(date_value) == 2:
            date_value = (max(min_date, date_value[0]), min(max_date, date_value[1]))
        date_range = st.date_input("Review date range (UTC)", value=date_value, min_value=min_date, max_value=max_date, key="filter_dates")
    else:
        date_range = None
    st.markdown("---")
    st.caption("Filters apply to metrics, charts, tables and downloads.")

filtered = data[data["rating"].isin(selected_ratings)].copy()
if all_versions and len(selected_versions) < len(all_versions):
    filtered = filtered[filtered["app_version"].isin(selected_versions) | filtered["app_version"].eq("")]
if date_range and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start = pd.Timestamp(date_range[0], tz="UTC")
    end = pd.Timestamp(date_range[1], tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    filtered = filtered[filtered["review_date"].isna() | filtered["review_date"].between(start, end)]
if selected_themes:
    filtered = filtered[filtered["all_categories"].apply(lambda value: any(theme in str(value).split(";") for theme in selected_themes))]
else:
    filtered = filtered.iloc[0:0]

# Header
header_left, header_right = st.columns([5, 1.3], vertical_alignment="center")
with header_left:
    st.markdown('<div class="eyebrow">PRODUCT FEEDBACK ANALYTICS</div>', unsafe_allow_html=True)
    st.title(APP_TITLE)
    st.markdown('<div class="subtle">Turn public app reviews into transparent, evidence-led product priorities.</div>', unsafe_allow_html=True)
with header_right:
    st.markdown("**Purpose**")
    st.caption("Find patterns. Inspect evidence. Prioritize investigation.")

st.markdown("")
meta1, meta2, meta3 = st.columns([1.15, 1.25, 1.7])
meta1.caption("Source · Google Play public reviews")
meta2.caption(f"Dataset · {len(clean):,} valid unique reviews")
meta3.caption(f"Date coverage · {date_coverage(data)}")
st.info("Prototype note: issue labels use explainable keyword rules, not validated AI classification. Findings are investigation leads—not confirmed root causes.")

if filtered.empty:
    st.warning("No reviews match the current filters. Adjust the sidebar filters or select Reset filters.")
    st.stop()

n = len(filtered)
low = filtered[filtered["low_rating"]]
low_n = len(low)
mean_rating = filtered["rating"].mean()
text_n = int(filtered["has_text"].sum())
version_n = filtered.loc[filtered["app_version"].str.strip().ne(""), "app_version"].nunique()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Reviews analyzed", f"{n:,}", help="Number of reviews remaining after filters.")
m2.metric("Mean sample rating", f"{mean_rating:.2f} / 5", help="Average star rating in the filtered sample.")
m3.metric("Low-rated reviews (1–2 stars)", f"{low_n:,}", help=f"{(low_n/n*100):.1f}% of filtered reviews")
st.caption(f"Low-rated share: {low_n / n * 100:.1f}% of the filtered sample")
m4.metric("App versions represented", f"{version_n:,}", help="Unique non-empty app versions in the filtered sample.")

st.markdown("")
st.subheader("Investigation priorities")
st.caption("Ranked by multi-label keyword matches in low-rated reviews. A review can match multiple themes, so theme percentages do not sum to 100%. Treat these as investigation hypotheses until validated with telemetry and manually reviewed examples.")

# Use the same multi-label counting method as the issue chart so priorities and chart agree.
priority_counts = theme_counts(low)
priority_items = [(cat, int(count)) for cat, count in priority_counts.items() if cat != "General / Uncategorized"][:5]
if not priority_items:
    st.info("No 1–2 star reviews match a defined issue theme under the current filters.")
else:
    priority_cols = st.columns(min(5, len(priority_items)))
    for idx, (category, count) in enumerate(priority_items):
        with priority_cols[idx]:
            share = count / max(low_n, 1) * 100
            st.markdown(f"""
            <div class="priority-card">
              <div class="priority-rank">PRIORITY {idx + 1:02d}</div>
              <div class="priority-title">{category}</div>
              <div class="priority-meta">{count:,} primary-label reviews · {share:.1f}% of low-rated reviews</div>
              <div class="priority-tag">Investigate</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("")
chart1, chart2 = st.columns([1, 1.25])
with chart1:
    with st.container(border=True):
        st.subheader("Rating distribution")
        st.caption(f"Star ratings across {n:,} filtered reviews")
        rating_dist = filtered["rating"].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
        rating_df = rating_dist.rename_axis("Stars").rename("Reviews").reset_index()
        rating_df["Stars"] = rating_df["Stars"].astype(str) + " star"
        st.bar_chart(rating_df, x="Stars", y="Reviews", color="#2775e8")
        st.caption("The sample is self-selected; this is not the app's official Play Store rating.")
with chart2:
    with st.container(border=True):
        st.subheader("Issue themes in low-rated reviews")
        st.caption("Counts use the same multi-label keyword matches as the priority cards; one review can contribute to multiple themes.")
        counts = theme_counts(low)
        if counts.empty:
            st.write("No defined issue-theme matches in the current low-rated subset.")
        else:
            theme_df = counts.rename_axis("Issue theme").rename("Reviews").reset_index().sort_values("Reviews", ascending=True)
            st.bar_chart(theme_df, x="Issue theme", y="Reviews", horizontal=True, color="#2775e8")

trend_col, version_col = st.columns([1.1, 1])
with trend_col:
    with st.container(border=True):
        st.subheader("Rating trend over time")
        st.caption("Monthly mean rating; months with no dated reviews are omitted.")
        dated = filtered.dropna(subset=["review_date"]).copy()
        if dated.empty:
            st.caption("No usable review dates in this filtered dataset.")
        else:
            monthly = dated.set_index("review_date").resample("MS")["rating"].agg(["mean", "count"]).dropna()
            monthly = monthly.rename(columns={"mean": "Mean rating", "count": "Reviews"})
            st.line_chart(monthly[["Mean rating"]], y="Mean rating", color="#2775e8")
            st.caption(f"{len(monthly)} months represented · hover or inspect the table for counts.")
with version_col:
    with st.container(border=True):
        st.subheader("Rating by app version")
        st.caption("Descriptive comparison; versions may have different sample sizes.")
        version_data = filtered[filtered["app_version"].str.strip().ne("")].groupby("app_version").agg(
            reviews=("rating", "size"),
            mean_rating=("rating", "mean"),
            low_star_share=("low_rating", "mean"),
        ).sort_values("reviews", ascending=False).head(15)
        if version_data.empty:
            st.caption("No app-version values available.")
        else:
            version_display = version_data.reset_index().rename(columns={
                "app_version": "App version", "reviews": "Reviews",
                "mean_rating": "Mean rating", "low_star_share": "1–2 star share",
            })
            version_display["Mean rating"] = version_display["Mean rating"].round(2)
            version_display["1–2 star share"] = (version_display["1–2 star share"] * 100).round(1)
            st.dataframe(
                version_display,
                use_container_width=True,
                hide_index=True,
                height=350,
                column_config={
                    "Reviews": st.column_config.NumberColumn("Reviews", format="%d"),
                    "Mean rating": st.column_config.NumberColumn("Mean rating", format="%.2f"),
                    "1–2 star share": st.column_config.NumberColumn("1–2 star (%)", format="%.1f%%"),
                },
            )

st.markdown("")
with st.container(border=True):
    explorer_header, download_col = st.columns([4, 1.2], vertical_alignment="center")
    with explorer_header:
        st.subheader("Review explorer")
        st.caption("Search the original feedback behind the aggregate patterns.")
    with download_col:
        st.download_button(
            "Download filtered CSV",
            data=filtered.to_csv(index=False).encode("utf-8-sig"),
            file_name="moveinsync_filtered_reviews.csv",
            mime="text/csv",
            use_container_width=True,
        )
    search = st.text_input("Search review text", placeholder="Search for login, booking, ETA, crash…", key="review_search")
    explorer = filtered.copy()
    if search.strip():
        explorer = explorer[explorer["review_text"].str.contains(re.escape(search.strip()), case=False, na=False)]
    explorer = explorer.sort_values("review_date", ascending=False, na_position="last")
    st.caption(f"{len(explorer):,} matching reviews")
    show_cols = [c for c in ["review_date", "rating", "app_version", "primary_category", "all_categories", "review_text", "helpful_votes", "developer_reply"] if c in explorer.columns]
    display = explorer[show_cols].copy()
    if "review_date" in display:
        display["review_date"] = display["review_date"].dt.strftime("%Y-%m-%d")
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "review_date": st.column_config.TextColumn("Review date", width="small"),
            "rating": st.column_config.NumberColumn("Rating", min_value=1, max_value=5, format="%d ★"),
            "app_version": st.column_config.TextColumn("App version", width="small"),
            "primary_category": st.column_config.TextColumn("Primary theme", width="medium"),
            "all_categories": st.column_config.TextColumn("Matched themes", width="large"),
            "review_text": st.column_config.TextColumn("Review text", width="large"),
            "helpful_votes": st.column_config.NumberColumn("Helpful votes", format="%d"),
            "developer_reply": st.column_config.TextColumn("Developer reply", width="large"),
        },
    )

download_col1, download_col2 = st.columns(2)
with download_col1:
    st.download_button(
        "Download analysis report (Markdown)",
        data=make_report(filtered).encode("utf-8"),
        file_name="moveinsync_review_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
with download_col2:
    analyzed_csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download analyzed dataset (CSV)",
        data=analyzed_csv,
        file_name="moveinsync_analyzed_reviews.csv",
        mime="text/csv",
        use_container_width=True,
    )

with st.expander("Methodology, definitions and limitations"):
    st.markdown("""
    **How issue labels work**
    - Transparent keyword rules assign a primary theme using the first matching category.
    - Additional matching themes are retained in `all_categories`.
    - A review may match multiple themes, so multi-theme chart counts can exceed the number of low-rated reviews.
    - “Low-rated” means a 1- or 2-star review. It is based on the rating, not inferred text sentiment.

    **Interpretation guardrails**
    - This dashboard analyzes a self-selected public review sample, not all app users.
    - Keyword labels can miss synonyms, match unrelated wording, and lose context.
    - App-version comparisons and rating trends are descriptive, not causal.
    - Validate hypotheses against manually labeled reviews, authorized operational telemetry, release history, and support outcomes before recommending a fix.
    """)
    st.caption(f"Dashboard generated {datetime.now(timezone.utc):%d %b %Y, %H:%M UTC}.")
