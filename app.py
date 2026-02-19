from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st

APP_TITLE = "Tasbeeh Tracker"
DB_PATH = Path(__file__).parent / "data" / "tasbeeh_tracker.db"
NAME_COOKIE = "tasbeeh_display_name"
ACCESS_COOKIE = "tasbeeh_access_ok"

CATEGORIES = [
    "Tasbeeh",
    "Zikr",
    "Quran Recitation / Verses",
    "Ahadith",
    "Other Good Deeds",
    "Sadaqah",
]

AYAT_OPTIONS = [
    {
        "ref": "Qur'an 2:286",
        "text": "Allah does not burden a soul beyond that it can bear.",
    },
    {
        "ref": "Qur'an 13:28",
        "text": "Verily, in the remembrance of Allah do hearts find rest.",
    },
    {
        "ref": "Qur'an 94:5-6",
        "text": "Indeed, with hardship comes ease. Indeed, with hardship comes ease.",
    },
    {
        "ref": "Qur'an 14:7",
        "text": "If you are grateful, I will surely increase you.",
    },
]

HADITH_OPTIONS = [
    {
        "ref": "Sahih Muslim",
        "text": "The most beloved deeds to Allah are those done regularly, even if small.",
    },
    {
        "ref": "Sahih Bukhari",
        "text": "The believer's shade on the Day of Resurrection will be his charity.",
    },
    {
        "ref": "Riyad as-Salihin",
        "text": "Whoever guides to good will have a reward like the doer of it.",
    },
    {
        "ref": "Sahih Muslim",
        "text": "Supplication for your brother in his absence is answered.",
    },
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
    cols = {
        row[1] for row in conn.execute("PRAGMA table_info(contributions)").fetchall()
    }
    if not cols:
        return

    if "entered_by" not in cols:
        # Old schema used `member`; map it into the new `entered_by`.
        conn.execute("ALTER TABLE contributions ADD COLUMN entered_by TEXT")
        if "member" in cols:
            conn.execute(
                "UPDATE contributions SET entered_by = COALESCE(entered_by, member, 'Family')"
            )
        else:
            conn.execute(
                "UPDATE contributions SET entered_by = COALESCE(entered_by, 'Family')"
            )

    if "category" not in cols:
        # Old schema used `type`; map it into the new `category`.
        conn.execute("ALTER TABLE contributions ADD COLUMN category TEXT")
        if "type" in cols:
            conn.execute(
                "UPDATE contributions SET category = COALESCE(category, type, 'Other Good Deeds')"
            )
        else:
            conn.execute(
                "UPDATE contributions SET category = COALESCE(category, 'Other Good Deeds')"
            )

    if "amount_pkr" not in cols:
        conn.execute(
            "ALTER TABLE contributions ADD COLUMN amount_pkr INTEGER NOT NULL DEFAULT 0"
        )

    if "count" not in cols:
        conn.execute("ALTER TABLE contributions ADD COLUMN count INTEGER NOT NULL DEFAULT 1")

    conn.execute(
        "UPDATE contributions SET entered_by = COALESCE(NULLIF(TRIM(entered_by), ''), 'Family')"
    )
    conn.execute(
        "UPDATE contributions SET category = COALESCE(NULLIF(TRIM(category), ''), 'Other Good Deeds')"
    )
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
          background: rgba(255,255,255,0.78);
          border: 1px solid rgba(28,36,30,0.14);
          border-radius: 16px;
          padding: 1rem 1rem;
          margin-bottom: .8rem;
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
        .card {
          background: rgba(255,255,255,0.80);
          border: 1px solid rgba(28,36,30,0.12);
          border-radius: 12px;
          padding: .8rem;
        }
        .small { color: #58645f; font-size: .9rem; }
        .stMetric {
          background: rgba(255,255,255,0.82);
          border: 1px solid rgba(28,36,30,0.14);
          border-radius: 12px;
          padding: 8px;
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

    remembered = cookies.get(ACCESS_COOKIE)
    if remembered == "ok":
        return

    st.sidebar.subheader("Family Access")
    code = st.sidebar.text_input("Enter family code", type="password")
    if st.sidebar.button("Unlock", use_container_width=True):
        if code == required_code:
            cookies.set(
                ACCESS_COOKIE,
                "ok",
                expires_at=datetime.utcnow() + timedelta(days=30),
            )
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


def add_entry(
    conn: sqlite3.Connection,
    entered_by: str,
    category: str,
    count: int,
    amount_pkr: int,
    note: str,
) -> None:
    conn.execute(
        """
        INSERT INTO contributions (created_at, entered_by, category, count, amount_pkr, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            entered_by,
            category,
            count,
            amount_pkr,
            note.strip() or None,
        ),
    )
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


def log_tab(conn: sqlite3.Connection, user_name: str) -> None:
    st.subheader("Add Deeds (Collective)")
    st.caption("Only family total is shown. Individual breakdown is hidden.")

    tabs = st.tabs(CATEGORIES)

    for idx, category in enumerate(CATEGORIES):
        with tabs[idx]:
            quick = st.columns(3)
            if quick[0].button("+1", key=f"{category}-q1", use_container_width=True):
                add_entry(conn, user_name, category, 1, 0, "")
                st.success("Added +1")
                st.rerun()
            if quick[1].button("+5", key=f"{category}-q5", use_container_width=True):
                add_entry(conn, user_name, category, 5, 0, "")
                st.success("Added +5")
                st.rerun()
            if quick[2].button("+10", key=f"{category}-q10", use_container_width=True):
                add_entry(conn, user_name, category, 10, 0, "")
                st.success("Added +10")
                st.rerun()

            with st.form(f"form-{category}", clear_on_submit=True):
                count = st.number_input(
                    f"Custom count for {category}",
                    min_value=1,
                    max_value=10000,
                    value=1,
                    step=1,
                    key=f"count-{category}",
                )
                amount_pkr = 0
                if category == "Sadaqah":
                    amount_pkr = st.number_input(
                        "Sadaqah amount in PKR",
                        min_value=1,
                        max_value=100000000,
                        value=100,
                        step=50,
                        key="sadaqah-pkr",
                    )
                note = st.text_input("Optional note", key=f"note-{category}")
                submitted = st.form_submit_button("Add", use_container_width=True)

                if submitted:
                    add_entry(conn, user_name, category, int(count), int(amount_pkr), note)
                    st.success("Contribution added.")
                    st.rerun()


def dashboard_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No entries yet. Add your first contribution.")
        return

    total_count = int(df["count"].sum())
    total_sadaqah_pkr = int(df["amount_pkr"].sum())
    today_utc = datetime.utcnow().date().isoformat()
    today_count = int(df[df["created_at"].str.startswith(today_utc)]["count"].sum())

    m1, m2, m3 = st.columns(3)
    m1.metric("Collective Total", f"{total_count}")
    m2.metric("Sadaqah (PKR)", f"{total_sadaqah_pkr:,}")
    m3.metric("Today Added", f"{today_count}")

    st.subheader("Category Totals")
    summary = (
        df.groupby("category", as_index=False)[["count", "amount_pkr"]]
        .sum()
        .sort_values("count", ascending=False)
    )
    summary["amount_pkr"] = summary["amount_pkr"].astype(int)
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.subheader("Recent Collective Activity")
    recent = df[["created_at", "category", "count", "amount_pkr", "note"]].copy()
    recent["created_at"] = pd.to_datetime(recent["created_at"], utc=True).dt.strftime("%Y-%m-%d %H:%M UTC")
    st.dataframe(recent.head(30), use_container_width=True, hide_index=True)


def inspiration_tab() -> None:
    ayah, hadith = daily_content()

    st.markdown("### Ayah of the Day")
    st.markdown(f"<div class='card'><strong>{ayah['ref']}</strong><br/>{ayah['text']}</div>", unsafe_allow_html=True)

    st.markdown("### Hadith of the Day")
    st.markdown(f"<div class='card'><strong>{hadith['ref']}</strong><br/>{hadith['text']}</div>", unsafe_allow_html=True)

    st.markdown("### Renowned Ahadith")
    for item in RENOWNED_HADITH:
        st.markdown(f"- {item}")


def settings_tab(conn: sqlite3.Connection, user_name: str) -> None:
    st.subheader("Reminder Settings")
    st.caption("Notifications are in-app reminders when you open this app.")
    rt, rx = get_pref(conn, user_name)

    with st.form("settings-form"):
        reminder_time = st.text_input("Preferred reminder time (24h)", value=rt, help="Example: 20:30")
        reminder_text = st.text_input("Reminder text", value=rx)
        save = st.form_submit_button("Save Reminder", use_container_width=True)

        if save:
            clean_text = reminder_text.strip() or "Take 5 minutes today for tasbeeh, zikr, or recitation."
            save_pref(conn, user_name, reminder_time.strip() or "20:00", clean_text)
            st.success("Reminder settings saved.")

    st.subheader("Privacy")
    st.markdown("- This app shows collective totals only.")
    st.markdown("- Name is saved only to recognize your own entries.")
    st.markdown("- For long-term stable cloud storage, move to Supabase.")


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

    tab1, tab2, tab3, tab4 = st.tabs(["Log", "Dashboard", "Daily", "Settings"])
    with tab1:
        log_tab(conn, user_name)
    with tab2:
        dashboard_tab(df)
    with tab3:
        inspiration_tab()
    with tab4:
        settings_tab(conn, user_name)


if __name__ == "__main__":
    main()
