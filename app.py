from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import altair as alt
import extra_streamlit_components as stx
import pandas as pd
import streamlit as st

APP_TITLE = "Tasbeeh Tracker"
DB_PATH = Path(__file__).parent / "data" / "tasbeeh_tracker.db"
NAME_COOKIE = "tasbeeh_display_name"
ACCESS_COOKIE = "tasbeeh_access_ok"

DEED_CATEGORIES = [
    "Zikr",
    "Quran Recitation / Verses",
    "Ahadith",
    "Other Good Deeds",
]
SADAQAH_CATEGORY = "Sadaqah"
CATEGORY_META = {
    "Zikr": {"icon": "🕊️", "color": "#2f7a57"},
    "Quran Recitation / Verses": {"icon": "📖", "color": "#3f8f74"},
    "Ahadith": {"icon": "🌙", "color": "#4d9687"},
    "Other Good Deeds": {"icon": "🤲", "color": "#5da18f"},
}

AYAT_OPTIONS = [
    {"ref": "Qur'an 2:286", "text": "Allah does not burden a soul beyond that it can bear."},
    {"ref": "Qur'an 13:28", "text": "Verily, in the remembrance of Allah do hearts find rest."},
    {"ref": "Qur'an 94:5-6", "text": "Indeed, with hardship comes ease. Indeed, with hardship comes ease."},
    {"ref": "Qur'an 14:7", "text": "If you are grateful, I will surely increase you."},
]

HADITH_OPTIONS = [
    {"ref": "Sahih Muslim", "text": "The most beloved deeds to Allah are those done regularly, even if small."},
    {"ref": "Sahih Bukhari", "text": "The believer's shade on the Day of Resurrection will be his charity."},
    {"ref": "Riyad as-Salihin", "text": "Whoever guides to good will have a reward like the doer of it."},
    {"ref": "Sahih Muslim", "text": "Supplication for your brother in his absence is answered."},
]

RENOWNED_HADITH = [
    "Actions are judged by intentions.",
    "Whoever believes in Allah and the Last Day should speak good or remain silent.",
    "None of you truly believes until he loves for his brother what he loves for himself.",
    "The strong person is the one who controls himself when angry.",
]


@st.cache_resource
def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            entered_by TEXT NOT NULL,
            category TEXT NOT NULL,
            count INTEGER NOT NULL,
            amount_pkr INTEGER NOT NULL DEFAULT 0,
            note TEXT
        )
        """
    )
    ensure_schema(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_prefs (
            user_name TEXT PRIMARY KEY,
            reminder_time TEXT NOT NULL DEFAULT '20:00',
            reminder_text TEXT NOT NULL DEFAULT 'Take 5 minutes today for tasbeeh, zikr, or recitation.'
        )
        """
    )
    conn.commit()
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(contributions)").fetchall()}
    if not cols:
        return

    if "entered_by" not in cols:
        conn.execute("ALTER TABLE contributions ADD COLUMN entered_by TEXT")
        if "member" in cols:
            conn.execute("UPDATE contributions SET entered_by = COALESCE(entered_by, member, 'Family')")
        else:
            conn.execute("UPDATE contributions SET entered_by = COALESCE(entered_by, 'Family')")

    if "category" not in cols:
        conn.execute("ALTER TABLE contributions ADD COLUMN category TEXT")
        if "type" in cols:
            conn.execute("UPDATE contributions SET category = COALESCE(category, type, 'Other Good Deeds')")
        else:
            conn.execute("UPDATE contributions SET category = COALESCE(category, 'Other Good Deeds')")

    if "count" not in cols:
        conn.execute("ALTER TABLE contributions ADD COLUMN count INTEGER NOT NULL DEFAULT 1")

    if "amount_pkr" not in cols:
        conn.execute("ALTER TABLE contributions ADD COLUMN amount_pkr INTEGER NOT NULL DEFAULT 0")

    conn.execute("UPDATE contributions SET entered_by = COALESCE(NULLIF(TRIM(entered_by), ''), 'Family')")
    conn.execute("UPDATE contributions SET category = COALESCE(NULLIF(TRIM(category), ''), 'Other Good Deeds')")
    conn.commit()


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap');
        .stApp {
          background: radial-gradient(circle at 0% 0%, #fff4e6 0%, #f6f7ef 45%, #edf4fb 100%);
          font-family: 'Inter', sans-serif;
        }
        .hero {
          background: rgba(255,255,255,0.80);
          border: 1px solid rgba(28,36,30,0.15);
          border-radius: 16px;
          padding: 1rem;
          margin-bottom: .9rem;
        }
        .hero-title {
          color: #1b3628;
          font-size: 1.8rem;
          margin: 0;
          font-family: 'Playfair Display', serif;
        }
        .hero-text { color: #3d4a43; margin: .4rem 0 0; line-height: 1.45; }
        .hero-dua {
          margin-top: .8rem;
          padding: .75rem .9rem;
          border-radius: 10px;
          background: #fff8ee;
          border: 1px solid #ecdcc8;
          color: #3e342a;
          line-height: 1.55;
        }
        .cat-box {
          background: rgba(255,255,255,0.86);
          border: 1px solid rgba(27,54,40,0.14);
          border-radius: 12px;
          padding: .75rem .8rem;
          margin-bottom: .45rem;
          min-height: 84px;
        }
        .cat-title { margin: 0; color: #183327; font-size: 1rem; font-weight: 700; }
        .cat-total { margin: .2rem 0 0; color: #51605a; font-size: .9rem; }
        .card {
          background: rgba(255,255,255,0.82);
          border: 1px solid rgba(28,36,30,0.12);
          border-radius: 12px;
          padding: .8rem;
        }
        .stMetric {
          background: rgba(255,255,255,0.82);
          border: 1px solid rgba(28,36,30,0.14);
          border-radius: 12px;
          padding: 8px;
        }
        .stButton > button {
          border-radius: 10px !important;
          border: 1px solid rgba(35,67,50,0.16) !important;
          font-weight: 600 !important;
        }
        .deed-chip {
          border: 1px solid rgba(35,67,50,0.14);
          border-radius: 10px;
          background: rgba(255,255,255,0.78);
          padding: .55rem .7rem;
          margin-bottom: .4rem;
          min-height: 78px;
        }
        .deed-chip-title {
          font-size: .95rem;
          color: #203b2d;
          margin: 0;
          font-weight: 700;
        }
        .deed-chip-total {
          color: #5b6963;
          margin: .2rem 0 0;
          font-size: .88rem;
        }
        @media (max-width: 768px) {
          .hero-title { font-size: 1.35rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def cookie_manager() -> stx.CookieManager:
    return stx.CookieManager()


def access_gate(cookies: stx.CookieManager) -> None:
    required_code = str(st.secrets.get("FAMILY_ACCESS_CODE", "")).strip()
    if not required_code:
        return

    if cookies.get(ACCESS_COOKIE) == "ok":
        return

    st.sidebar.subheader("Family Access")
    code = st.sidebar.text_input("Enter family code", type="password")
    if st.sidebar.button("Unlock", use_container_width=True):
        if code == required_code:
            cookies.set(ACCESS_COOKIE, "ok", expires_at=datetime.utcnow() + timedelta(days=30))
            st.rerun()
        st.sidebar.error("Incorrect access code")

    st.warning("This app is private. Enter family code in the sidebar.")
    st.stop()


def get_display_name(cookies: stx.CookieManager) -> str:
    saved_name = (cookies.get(NAME_COOKIE) or "").strip()
    if "display_name" not in st.session_state:
        st.session_state.display_name = saved_name

    st.sidebar.subheader("Your Name")
    typed_name = st.sidebar.text_input("Enter your name", value=st.session_state.display_name, max_chars=40)
    if st.sidebar.button("Save Name", use_container_width=True):
        clean = typed_name.strip()
        if not clean:
            st.sidebar.error("Name cannot be empty.")
        else:
            st.session_state.display_name = clean
            cookies.set(NAME_COOKIE, clean, expires_at=datetime.utcnow() + timedelta(days=365))
            st.sidebar.success("Name saved on this device.")

    final_name = (typed_name or st.session_state.display_name).strip()
    if not final_name:
        st.info("Enter your name in sidebar once to start logging.")
        st.stop()
    return final_name


def add_entry(conn: sqlite3.Connection, entered_by: str, category: str, count: int, amount_pkr: int, note: str) -> None:
    table_cols = {row[1] for row in conn.execute("PRAGMA table_info(contributions)").fetchall()}
    insert_cols: list[str] = ["created_at"]
    insert_vals: list[object] = [datetime.utcnow().isoformat()]

    if "entered_by" in table_cols:
        insert_cols.append("entered_by")
        insert_vals.append(entered_by)
    if "category" in table_cols:
        insert_cols.append("category")
        insert_vals.append(category)
    if "count" in table_cols:
        insert_cols.append("count")
        insert_vals.append(count)
    if "amount_pkr" in table_cols:
        insert_cols.append("amount_pkr")
        insert_vals.append(amount_pkr)
    if "note" in table_cols:
        insert_cols.append("note")
        insert_vals.append(note.strip() or None)

    # Legacy schema compatibility
    if "member" in table_cols:
        insert_cols.append("member")
        insert_vals.append(entered_by)
    if "type" in table_cols:
        insert_cols.append("type")
        insert_vals.append(category)

    placeholders = ", ".join(["?"] * len(insert_cols))
    cols_sql = ", ".join(insert_cols)
    conn.execute(f"INSERT INTO contributions ({cols_sql}) VALUES ({placeholders})", tuple(insert_vals))
    conn.commit()


def fetch_df(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT created_at, category, count, amount_pkr, COALESCE(note, '') AS note, entered_by
        FROM contributions
        ORDER BY created_at DESC
        """,
        conn,
    )


def category_count_map(df: pd.DataFrame) -> dict[str, int]:
    all_categories = DEED_CATEGORIES + [SADAQAH_CATEGORY]
    if df.empty:
        return {cat: 0 for cat in all_categories}
    summary = df.groupby("category", as_index=False)["count"].sum()
    counts = {row["category"]: int(row["count"]) for _, row in summary.iterrows()}
    return {cat: counts.get(cat, 0) for cat in all_categories}


def get_pref(conn: sqlite3.Connection, user_name: str) -> tuple[str, str]:
    row = conn.execute(
        "SELECT reminder_time, reminder_text FROM user_prefs WHERE user_name = ?",
        (user_name,),
    ).fetchone()
    if row:
        return str(row[0]), str(row[1])
    return "20:00", "Take 5 minutes today for tasbeeh, zikr, or recitation."


def save_pref(conn: sqlite3.Connection, user_name: str, reminder_time: str, reminder_text: str) -> None:
    conn.execute(
        """
        INSERT INTO user_prefs (user_name, reminder_time, reminder_text)
        VALUES (?, ?, ?)
        ON CONFLICT(user_name) DO UPDATE SET
            reminder_time = excluded.reminder_time,
            reminder_text = excluded.reminder_text
        """,
        (user_name, reminder_time, reminder_text),
    )
    conn.commit()


def show_reminder(conn: sqlite3.Connection, user_name: str) -> None:
    reminder_time, reminder_text = get_pref(conn, user_name)
    row = conn.execute(
        "SELECT created_at FROM contributions WHERE entered_by = ? ORDER BY created_at DESC LIMIT 1",
        (user_name,),
    ).fetchone()
    today = date.today()

    if row:
        last_date = datetime.fromisoformat(str(row[0])).date()
        if last_date < today:
            st.warning(f"Reminder ({reminder_time}): {reminder_text}")
    else:
        st.warning(f"Reminder ({reminder_time}): {reminder_text}")


def daily_content() -> tuple[dict[str, str], dict[str, str]]:
    idx_ayah = date.today().toordinal() % len(AYAT_OPTIONS)
    idx_hadith = (date.today().toordinal() * 3) % len(HADITH_OPTIONS)
    return AYAT_OPTIONS[idx_ayah], HADITH_OPTIONS[idx_hadith]


def top_section() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1 class="hero-title">Tasbeeh Tracker</h1>
          <p class="hero-text">
            For our beloved father <strong>Muhammad Ashraf</strong>.<br/>
            May Allah have mercy on him, forgive him, and grant him the highest place in Jannah. Ameen.
          </p>
          <div class="hero-dua">
            <strong>Dua:</strong><br/>
            O Allah, forgive Muhammad Ashraf completely, elevate his rank among the righteous, expand and illuminate his grave,
            replace his shortcomings with Your mercy, and grant him ease on the Day of Judgment.<br/>
            O Allah, accept every tasbeeh, recitation, charity, and dua we do as sadaqah jariyah for him, and unite us with him
            in Jannat al-Firdaws without reckoning. Ameen.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def deeds_tab(conn: sqlite3.Connection, user_name: str, df: pd.DataFrame) -> None:
    st.subheader("Collective Deeds")
    st.caption("Choose step size, then tap category button. Chart updates instantly.")

    counts = category_count_map(df)
    deed_totals = [counts.get(cat, 0) for cat in DEED_CATEGORIES]
    today_utc = datetime.utcnow().date().isoformat()
    today_total = int(df[df["created_at"].str.startswith(today_utc)]["count"].sum()) if not df.empty else 0
    all_total = int(sum(deed_totals))

    m1, m2 = st.columns(2)
    m1.metric("Total Deeds", all_total)
    m2.metric("Added Today", today_total)

    step = st.radio(
        "Tap increment",
        options=[1, 3, 5],
        horizontal=True,
        index=0,
        format_func=lambda x: f"+{x}",
    )

    chart_rows = pd.DataFrame(
        {
            "Category": DEED_CATEGORIES,
            "Total": deed_totals,
            "Color": [CATEGORY_META[c]["color"] for c in DEED_CATEGORIES],
        }
    )
    hover = alt.selection_point(on="mouseover", fields=["Category"], empty=True)
    bar = alt.Chart(chart_rows).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
        x=alt.X("Category:N", sort=DEED_CATEGORIES, axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y("Total:Q", title=None),
        color=alt.Color("Color:N", scale=None, legend=None),
        opacity=alt.condition(hover, alt.value(1.0), alt.value(0.85)),
        tooltip=["Category", "Total"],
    ).add_params(hover)
    labels = alt.Chart(chart_rows).mark_text(
        align="center", baseline="bottom", dy=-4, color="#1b3628", fontWeight="bold"
    ).encode(
        x=alt.X("Category:N", sort=DEED_CATEGORIES),
        y=alt.Y("Total:Q"),
        text=alt.Text("Total:Q"),
    )
    st.altair_chart((bar + labels).properties(height=320), use_container_width=True)

    cols = st.columns(len(DEED_CATEGORIES))
    for col, category in zip(cols, DEED_CATEGORIES):
        with col:
            icon = CATEGORY_META[category]["icon"]
            st.markdown(
                "<div class='deed-chip'>"
                f"<p class='deed-chip-title'>{icon} {category}</p>"
                f"<p class='deed-chip-total'>Total: {counts.get(category, 0)}</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"+{step}", key=f"btn-{category}", use_container_width=True):
                add_entry(conn, user_name, category, int(step), 0, "")
                st.toast(f"{icon} {category} +{step}")
                st.rerun()


def sadaqah_tab(conn: sqlite3.Connection, user_name: str, df: pd.DataFrame) -> None:
    st.subheader("Sadaqah")

    counts = category_count_map(df)
    sadaqah_count = counts.get(SADAQAH_CATEGORY, 0)
    total_pkr = int(df.loc[df["category"] == SADAQAH_CATEGORY, "amount_pkr"].sum()) if not df.empty else 0

    graph_df = pd.DataFrame(
        {"Metric": ["Sadaqah Entries", "Sadaqah PKR"], "Value": [sadaqah_count, total_pkr]}
    ).set_index("Metric")
    st.bar_chart(graph_df, y="Value", use_container_width=True)

    m1, m2 = st.columns(2)
    m1.metric("Sadaqah Entries", f"{sadaqah_count}")
    m2.metric("Total Sadaqah (PKR)", f"{total_pkr:,}")

    with st.form("sadaqah-pkr-form", clear_on_submit=True):
        amount_pkr = st.number_input("Amount (PKR)", min_value=1, max_value=100000000, value=100, step=50)
        note = st.text_input("Optional note")
        submitted = st.form_submit_button("Add Sadaqah", use_container_width=True)
        if submitted:
            add_entry(conn, user_name, SADAQAH_CATEGORY, 1, int(amount_pkr), note)
            st.success("Sadaqah added.")
            st.rerun()


def inspiration_section() -> None:
    ayah, hadith = daily_content()
    st.subheader("Daily Inspiration")
    st.markdown(f"<div class='card'><strong>Ayah of the Day ({ayah['ref']})</strong><br/>{ayah['text']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'><strong>Hadith of the Day ({hadith['ref']})</strong><br/>{hadith['text']}</div>", unsafe_allow_html=True)
    st.markdown("#### Renowned Ahadith")
    for item in RENOWNED_HADITH:
        st.markdown(f"- {item}")


def settings_section(conn: sqlite3.Connection, user_name: str) -> None:
    st.subheader("Reminder Settings")
    st.caption("In-app reminder appears when you open the app.")

    rt, rx = get_pref(conn, user_name)
    with st.form("settings-form"):
        reminder_time = st.text_input("Preferred reminder time (24h)", value=rt, help="Example: 20:30")
        reminder_text = st.text_input("Reminder text", value=rx)
        save = st.form_submit_button("Save Reminder", use_container_width=True)
        if save:
            clean_text = reminder_text.strip() or "Take 5 minutes today for tasbeeh, zikr, or recitation."
            save_pref(conn, user_name, reminder_time.strip() or "20:00", clean_text)
            st.success("Reminder settings saved.")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🤲", layout="wide")
    apply_styles()

    cookies = cookie_manager()
    access_gate(cookies)
    user_name = get_display_name(cookies)
    conn = get_conn()

    top_section()
    show_reminder(conn, user_name)
    df = fetch_df(conn)
    tabs = st.tabs(["Deeds", "Sadaqah", "Daily Content", "Settings"])
    with tabs[0]:
        deeds_tab(conn, user_name, df)
    with tabs[1]:
        sadaqah_tab(conn, user_name, fetch_df(conn))
    with tabs[2]:
        inspiration_section()
    with tabs[3]:
        settings_section(conn, user_name)


if __name__ == "__main__":
    main()
