from __future__ import annotations

import sqlite3
from datetime import date, datetime
import json
import random
from html import escape
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import altair as alt
import pandas as pd
import streamlit as st

APP_TITLE = "Tasbeeh Tracker"
DB_PATH = Path(__file__).parent / "data" / "tasbeeh_tracker.db"
DEFAULT_HADITH_API_KEY = "$2y$10$4rTM9bbsY1QuH0HE2W0gufDS33KuX32Kdi50kfx9v9LJHyA2K2y"

DEED_CATEGORIES = [
    "Zikr",
    "Quran Recitation / Verses",
    "Ahadith",
    "Other Good Deeds",
]
SADAQAH_CATEGORY = "Sadaqah"
CATEGORY_META = {
    "Zikr": {"icon": "🕊️", "color": "#1F7A5C"},
    "Quran Recitation / Verses": {"icon": "📖", "color": "#2F8E6C"},
    "Ahadith": {"icon": "🌙", "color": "#37A77E"},
    "Other Good Deeds": {"icon": "🤲", "color": "#57B993"},
}

AYAT_OPTIONS = [
    {
        "ref": "Qur'an 2:286",
        "arabic": "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا",
        "english": "Allah does not burden a soul beyond that it can bear.",
        "source": "Curated Backup",
    },
    {
        "ref": "Qur'an 13:28",
        "arabic": "أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ",
        "english": "Verily, in the remembrance of Allah do hearts find rest.",
        "source": "Curated Backup",
    },
    {
        "ref": "Qur'an 94:5-6",
        "arabic": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا ۝ إِنَّ مَعَ الْعُسْرِ يُسْرًا",
        "english": "Indeed, with hardship comes ease. Indeed, with hardship comes ease.",
        "source": "Curated Backup",
    },
    {
        "ref": "Qur'an 14:7",
        "arabic": "لَئِن شَكَرْتُمْ لَأَزِيدَنَّكُمْ",
        "english": "If you are grateful, I will surely increase you.",
        "source": "Curated Backup",
    },
]

HADITH_OPTIONS = [
    {
        "ref": "Sahih Bukhari & Sahih Muslim",
        "arabic": "إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ",
        "english": "Actions are judged by intentions.",
        "source": "Curated Backup",
    },
    {
        "ref": "Sahih Bukhari & Sahih Muslim",
        "arabic": "مَنْ كَانَ يُؤْمِنُ بِاللَّهِ وَالْيَوْمِ الآخِرِ فَلْيَقُلْ خَيْرًا أَوْ لِيَصْمُتْ",
        "english": "Whoever believes in Allah and the Last Day should speak good or remain silent.",
        "source": "Curated Backup",
    },
    {
        "ref": "Sahih Muslim",
        "arabic": "لَا يُؤْمِنُ أَحَدُكُمْ حَتَّى يُحِبَّ لِأَخِيهِ مَا يُحِبُّ لِنَفْسِهِ",
        "english": "None of you truly believes until he loves for his brother what he loves for himself.",
        "source": "Curated Backup",
    },
    {
        "ref": "Sahih Bukhari & Sahih Muslim",
        "arabic": "لَيْسَ الشَّدِيدُ بِالصُّرَعَةِ، إِنَّمَا الشَّدِيدُ الَّذِي يَمْلِكُ نَفْسَهُ عِنْدَ الغَضَبِ",
        "english": "The strong person is the one who controls himself when angry.",
        "source": "Curated Backup",
    },
]

@st.cache_resource
def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
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
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&family=Noto+Naskh+Arabic:wght@500;600&display=swap');
        .stApp {
          background:
            radial-gradient(circle at 12% 12%, rgba(118, 197, 163, 0.30), rgba(255,255,255,0) 28%),
            radial-gradient(circle at 88% 8%, rgba(189, 226, 210, 0.28), rgba(255,255,255,0) 30%),
            radial-gradient(circle at 80% 82%, rgba(141, 209, 178, 0.22), rgba(255,255,255,0) 34%),
            linear-gradient(150deg, #eaf6f0 0%, #e5f3ec 46%, #ddf2ea 100%);
          font-family: 'Inter', sans-serif;
        }
        .block-container {
          max-width: 1080px;
          padding-top: 1rem;
          padding-bottom: 2.5rem;
        }
        .hero {
          background: linear-gradient(135deg, rgba(255,255,255,0.33), rgba(255,255,255,0.16));
          backdrop-filter: blur(20px) saturate(140%);
          -webkit-backdrop-filter: blur(20px) saturate(140%);
          border: 1px solid rgba(255,255,255,0.48);
          border-radius: 20px;
          padding: 1.1rem;
          margin-bottom: 1rem;
          box-shadow: 0 18px 42px rgba(39, 78, 117, 0.2), inset 0 1px 0 rgba(255,255,255,0.6);
        }
        .hero-title {
          color: #173f35;
          font-size: 1.8rem;
          margin: 0;
          font-family: 'Playfair Display', serif;
          text-shadow: 0 2px 14px rgba(255,255,255,0.5);
        }
        .hero-text { color: #245245; margin: .4rem 0 0; line-height: 1.45; }
        .hero-dua {
          margin-top: .8rem;
          padding: .85rem 1rem;
          border-radius: 10px;
          background: linear-gradient(135deg, rgba(255,255,255,0.38), rgba(255,255,255,0.18));
          border: 1px solid rgba(255,255,255,0.54);
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          color: #20473d;
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
          background: linear-gradient(135deg, rgba(255,255,255,0.35), rgba(255,255,255,0.16));
          border: 1px solid rgba(255,255,255,0.45);
          border-radius: 12px;
          padding: .8rem;
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          box-shadow: 0 10px 28px rgba(23, 63, 53, 0.13);
        }
        .daily-card {
          background: linear-gradient(135deg, rgba(255,255,255,0.38), rgba(255,255,255,0.18));
          border: 1px solid rgba(255,255,255,0.5);
          border-radius: 14px;
          padding: 1rem;
          min-height: 170px;
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          box-shadow: 0 12px 30px rgba(25, 78, 63, 0.16), inset 0 1px 0 rgba(255,255,255,0.6);
        }
        .daily-title {
          margin: 0 0 .4rem 0;
          color: #173f35;
          font-size: 1rem;
          font-weight: 700;
        }
        .daily-ref {
          color: #2b6153;
          font-size: .88rem;
          margin-bottom: .4rem;
        }
        .daily-text {
          color: #234b40;
          line-height: 1.65;
          font-size: 1rem;
          margin: 0;
        }
        .daily-arabic {
          font-size: 1.28rem;
          line-height: 2.05;
          color: #123b31;
          direction: rtl;
          text-align: right;
          font-family: 'Noto Naskh Arabic', 'Amiri', serif;
          margin: .3rem 0 .6rem 0;
          background: rgba(255,255,255,0.28);
          border: 1px solid rgba(255,255,255,0.4);
          border-radius: 10px;
          padding: .55rem .65rem;
        }
        .daily-source {
          margin-top: .45rem;
          font-size: .8rem;
          color: #2c6354;
        }
        .daily-english-label {
          margin: .45rem 0 .2rem;
          font-size: .82rem;
          color: #2f5d50;
          letter-spacing: .02em;
          text-transform: uppercase;
          font-weight: 600;
        }
        .stMetric {
          background: linear-gradient(135deg, rgba(255,255,255,0.34), rgba(255,255,255,0.17));
          border: 1px solid rgba(255,255,255,0.52);
          border-radius: 12px;
          padding: 8px;
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
        }
        .stButton > button {
          border-radius: 12px !important;
          border: 1px solid rgba(255,255,255,0.45) !important;
          font-weight: 600 !important;
          color: #fff !important;
          background: linear-gradient(135deg, rgba(31, 122, 92, 0.88), rgba(55, 167, 126, 0.86)) !important;
          box-shadow: 0 10px 24px rgba(31, 122, 92, 0.32) !important;
          transition: transform .15s ease, box-shadow .15s ease !important;
        }
        .stButton > button:hover {
          transform: translateY(-1px);
          box-shadow: 0 14px 26px rgba(31, 122, 92, 0.40) !important;
        }
        .deed-chip {
          border: 1px solid rgba(255,255,255,0.45);
          border-radius: 14px;
          background: linear-gradient(145deg, rgba(255,255,255,0.34), rgba(255,255,255,0.16));
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          padding: .6rem .72rem;
          margin-bottom: .4rem;
          min-height: 78px;
          box-shadow: 0 10px 24px rgba(24, 74, 60, 0.16);
        }
        .deed-chip-title {
          font-size: .95rem;
          color: #173f35;
          margin: 0;
          font-weight: 700;
        }
        .deed-chip-total {
          color: #285a4d;
          margin: .2rem 0 0;
          font-size: .88rem;
        }
        [data-baseweb="tab-list"] {
          gap: 0.35rem;
          background: linear-gradient(135deg, rgba(255,255,255,0.30), rgba(255,255,255,0.14));
          border: 1px solid rgba(255,255,255,0.44);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border-radius: 14px;
          padding: .36rem;
          width: fit-content;
          box-shadow: 0 12px 24px rgba(24, 74, 60, 0.16);
        }
        [data-baseweb="tab"] {
          border-radius: 10px !important;
          padding: .4rem .8rem !important;
        }
        @media (max-width: 768px) {
          .hero-title { font-size: 1.35rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    # Keep daily cards stable during rapid counter clicks; refresh only on demand.
    if "daily_cards" not in st.session_state:
        st.session_state.daily_cards = {
            "ayah": fetch_ayah_of_day(),
            "hadith": fetch_hadith_of_day(),
            "loaded_at": datetime.utcnow().isoformat(),
        }
    cards = st.session_state.daily_cards
    return cards["ayah"], cards["hadith"]


def refresh_daily_content() -> None:
    st.session_state.daily_cards = {
        "ayah": fetch_ayah_of_day(),
        "hadith": fetch_hadith_of_day(),
        "loaded_at": datetime.utcnow().isoformat(),
    }


def fetch_json(url: str) -> dict:
    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return {}


def fetch_ayah_of_day() -> dict[str, str]:
    # Random ayah on each app load.
    ayah_number = random.SystemRandom().randint(1, 6236)
    url = f"https://api.alquran.cloud/v1/ayah/{ayah_number}/editions/quran-uthmani,en.asad"
    payload = fetch_json(url)
    data = payload.get("data", []) if isinstance(payload, dict) else []
    if isinstance(data, list) and len(data) >= 2:
        ar_data = data[0] if isinstance(data[0], dict) else {}
        en_data = data[1] if isinstance(data[1], dict) else {}
        arabic = str(ar_data.get("text", "")).strip()
        english = str(en_data.get("text", "")).strip()
        surah = ar_data.get("surah", {}) if isinstance(ar_data.get("surah", {}), dict) else {}
        surah_no = surah.get("number")
        ayah_in_surah = ar_data.get("numberInSurah")
        if arabic and english and surah_no and ayah_in_surah:
            return {
                "ref": f"Qur'an {surah_no}:{ayah_in_surah}",
                "arabic": arabic,
                "english": english,
                "source": "AlQuran.cloud",
            }

    # Fallback path for single-edition responses
    single_url_ar = f"https://api.alquran.cloud/v1/ayah/{ayah_number}/quran-uthmani"
    single_url_en = f"https://api.alquran.cloud/v1/ayah/{ayah_number}/en.asad"
    ar_payload = fetch_json(single_url_ar)
    en_payload = fetch_json(single_url_en)
    ar_data = ar_payload.get("data", {}) if isinstance(ar_payload, dict) else {}
    en_data = en_payload.get("data", {}) if isinstance(en_payload, dict) else {}
    arabic = str(ar_data.get("text", "")).strip()
    english = str(en_data.get("text", "")).strip()
    surah = ar_data.get("surah", {}) if isinstance(ar_data.get("surah", {}), dict) else {}
    surah_no = surah.get("number")
    ayah_in_surah = ar_data.get("numberInSurah")
    if arabic and english and surah_no and ayah_in_surah:
        return {
            "ref": f"Qur'an {surah_no}:{ayah_in_surah}",
            "arabic": arabic,
            "english": english,
            "source": "AlQuran.cloud",
        }

    return random.choice(AYAT_OPTIONS)


def first_non_empty(obj: dict, keys: list[str]) -> str:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def fetch_hadith_of_day() -> dict[str, str]:
    try:
        api_key = str(st.secrets.get("HADITH_API_KEY", DEFAULT_HADITH_API_KEY)).strip()
    except Exception:
        api_key = DEFAULT_HADITH_API_KEY
    if not api_key:
        return random.choice(HADITH_OPTIONS)

    try:
        base = str(st.secrets.get("HADITH_API_BASE_URL", "https://hadithapi.com/api")).rstrip("/")
    except Exception:
        base = "https://hadithapi.com/api"

    query_sets = [
        {"apiKey": api_key, "paginate": "1"},
        {"api_key": api_key, "paginate": "1"},
        {"apiKey": api_key},
        {"api_key": api_key},
    ]
    paths = ["/hadiths", "/hadith", "/books"]

    for path in paths:
        for query in query_sets:
            url = f"{base}{path}?{urlencode(query)}"
            payload = fetch_json(url)
            if not isinstance(payload, dict):
                continue

            data = payload.get("hadiths") or payload.get("data") or payload.get("hadith")
            entries = []
            if isinstance(data, dict):
                if isinstance(data.get("data"), list):
                    entries = data.get("data", [])
                else:
                    entries = [data]
            elif isinstance(data, list):
                entries = data

            entries = [e for e in entries if isinstance(e, dict)]
            if not entries:
                continue

            chosen = random.SystemRandom().choice(entries)
            english = first_non_empty(
                chosen,
                [
                    "hadithEnglish",
                    "hadith_english",
                    "englishNarrator",
                    "text",
                    "text_en",
                ],
            )
            arabic = first_non_empty(
                chosen,
                [
                    "hadithArabic",
                    "hadith_ar",
                    "arabic",
                    "text_ar",
                    "hadithArabicText",
                ],
            )
            source = first_non_empty(
                chosen,
                ["book", "bookName", "collection", "source", "chapterEnglish"],
            ) or "Hadith API"
            hadith_no = first_non_empty(
                chosen,
                ["hadithNumber", "hadith_number", "number", "hadithNo"],
            )
            if hadith_no:
                source = f"{source} #{hadith_no}"

            if english and arabic:
                return {"ref": source, "arabic": arabic, "english": english, "source": "HadithAPI"}

    return random.choice(HADITH_OPTIONS)


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


def front_daily_cards() -> None:
    ayah, hadith = daily_content()
    top_left, top_right = st.columns([4, 1])
    with top_right:
        if st.button("Refresh Daily", use_container_width=True):
            refresh_daily_content()
            st.rerun()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            (
                "<div class='daily-card'>"
                "<p class='daily-title'>Ayat of the Day</p>"
                f"<div class='daily-ref'>{escape(ayah.get('ref', 'Quran'))}</div>"
                f"<p class='daily-arabic'>{escape(ayah.get('arabic', ''))}</p>"
                "<div class='daily-english-label'>English Translation</div>"
                f"<p class='daily-text'>{escape(ayah.get('english', ''))}</p>"
                f"<div class='daily-source'>Source: {escape(ayah.get('source', 'Curated Backup'))}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            (
                "<div class='daily-card'>"
                "<p class='daily-title'>Hadees of the Day</p>"
                f"<div class='daily-ref'>{escape(hadith.get('ref', 'Hadith'))}</div>"
                f"<p class='daily-arabic'>{escape(hadith.get('arabic', ''))}</p>"
                "<div class='daily-english-label'>English Translation</div>"
                f"<p class='daily-text'>{escape(hadith.get('english', ''))}</p>"
                f"<div class='daily-source'>Source: {escape(hadith.get('source', 'Curated Backup'))}</div>"
                "</div>"
            ),
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
        y=alt.Y("Total:Q", title=None, axis=alt.Axis(grid=True)),
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
    st.altair_chart(
        (bar + labels).properties(height=330).configure_axis(gridColor="#d9e8de"),
        use_container_width=True,
    )

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
    )
    s_bar = alt.Chart(graph_df).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
        x=alt.X("Metric:N", axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y("Value:Q", axis=alt.Axis(grid=True), title=None),
        color=alt.value("#3f9169"),
        tooltip=["Metric", "Value"],
    )
    s_lbl = alt.Chart(graph_df).mark_text(
        align="center", baseline="bottom", dy=-4, color="#1b3628", fontWeight="bold"
    ).encode(x="Metric:N", y="Value:Q", text="Value:Q")
    st.altair_chart((s_bar + s_lbl).properties(height=260), use_container_width=True)

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

    user_name = "Family"
    conn = get_conn()

    top_section()
    front_daily_cards()
    show_reminder(conn, user_name)
    df = fetch_df(conn)
    tabs = st.tabs(["Deeds", "Sadaqah", "Settings"])
    with tabs[0]:
        deeds_tab(conn, user_name, df)
    with tabs[1]:
        sadaqah_tab(conn, user_name, fetch_df(conn))
    with tabs[2]:
        settings_section(conn, user_name)


if __name__ == "__main__":
    main()
