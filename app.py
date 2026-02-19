from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "Family Sadaqa & Recitation"
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "family_counter.db"

REMINDERS = [
    "A small daily deed done consistently can become a lasting charity.",
    "Take five minutes for recitation and make dua for our father today.",
    "Even one good action today is valuable. Keep it simple and sincere.",
    "Consistency over quantity. One step each day as a family.",
    "Do one private act of sadaqa today and log it here.",
]


def get_members() -> list[str]:
    raw = st.secrets.get("FAMILY_MEMBERS", "Sibling 1,Sibling 2,Sibling 3,Sibling 4")
    return [name.strip() for name in raw.split(",") if name.strip()]


@st.cache_resource
def get_conn() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            member TEXT NOT NULL,
            kind TEXT NOT NULL,
            amount INTEGER NOT NULL,
            note TEXT
        )
        """
    )
    conn.commit()
    return conn


def apply_access_gate() -> None:
    required_code = st.secrets.get("FAMILY_ACCESS_CODE", "").strip()
    if not required_code:
        return

    st.sidebar.subheader("Family Access")
    code = st.sidebar.text_input("Enter access code", type="password")
    if code != required_code:
        st.warning("Access code required. Ask the family admin for the code.")
        st.stop()


def add_contribution(conn: sqlite3.Connection, member: str, kind: str, amount: int, note: str) -> None:
    conn.execute(
        """
        INSERT INTO contributions (created_at, member, kind, amount, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (datetime.utcnow().isoformat(), member.strip(), kind, amount, note.strip() or None),
    )
    conn.commit()


def fetch_data(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            id,
            created_at,
            member,
            kind,
            amount,
            COALESCE(note, '') AS note
        FROM contributions
        ORDER BY id DESC
        """,
        conn,
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: radial-gradient(circle at 10% 10%, #f9efe3, #f2f7f2 45%, #e9f0f6 100%);
            }
            .hero {
                border: 1px solid rgba(42, 36, 31, 0.12);
                border-radius: 18px;
                padding: 1rem 1.25rem;
                background: rgba(255, 255, 255, 0.72);
                backdrop-filter: blur(2px);
                margin-bottom: 1rem;
            }
            .hero h1 {
                margin: 0;
                font-size: 2rem;
                color: #1f2f28;
            }
            .hero p {
                margin-top: .45rem;
                color: #4d5954;
            }
            .reminder {
                background: #fffaf4;
                border: 1px solid #ead8c6;
                border-radius: 12px;
                padding: .8rem 1rem;
                color: #4b3f33;
                margin: .75rem 0 0.25rem;
            }
            .stMetric {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(31, 47, 40, 0.12);
                border-radius: 14px;
                padding: 8px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🤲", layout="wide")
    inject_styles()
    apply_access_gate()

    conn = get_conn()

    st.markdown(
        """
        <div class="hero">
            <h1>Family Sadaqa & Recitation</h1>
            <p>Shared tracker for siblings to contribute recitation, sadaqa, and other good deeds in memory of our father.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "reminder_idx" not in st.session_state:
        st.session_state.reminder_idx = 0

    reminder_col, btn_col = st.columns([5, 1])
    with reminder_col:
        st.markdown(f"<div class='reminder'><strong>Daily Reminder:</strong> {REMINDERS[st.session_state.reminder_idx]}</div>", unsafe_allow_html=True)
    with btn_col:
        if st.button("New", use_container_width=True):
            st.session_state.reminder_idx = (st.session_state.reminder_idx + 1) % len(REMINDERS)
            st.rerun()

    members = get_members()

    with st.form("add_form", clear_on_submit=True):
        st.subheader("Add Contribution")
        c1, c2, c3 = st.columns(3)
        with c1:
            selected = st.selectbox("Member", options=members + ["Other"], index=0)
            custom_name = st.text_input("If Other, enter name") if selected == "Other" else ""
        with c2:
            kind = st.selectbox("Type", ["Recitation", "Sadaqa", "Dua", "Other Good Deed"], index=0)
        with c3:
            amount = st.number_input("Count", min_value=1, max_value=1000, value=1, step=1)

        note = st.text_input("Optional note", placeholder="Example: after Maghrib, food donation, etc.")
        submitted = st.form_submit_button("Add", use_container_width=True)

        if submitted:
            member = custom_name.strip() if selected == "Other" else selected
            if not member:
                st.error("Please enter a member name.")
            else:
                add_contribution(conn, member, kind, int(amount), note)
                st.success("Contribution added.")

    df = fetch_data(conn)

    if df.empty:
        st.info("No entries yet. Add the first contribution above.")
        return

    total_count = int(df["amount"].sum())
    total_recitation = int(df.loc[df["kind"] == "Recitation", "amount"].sum())
    total_sadaqa = int(df.loc[df["kind"] == "Sadaqa", "amount"].sum())

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Contributions", f"{total_count}")
    m2.metric("Total Recitations", f"{total_recitation}")
    m3.metric("Total Sadaqa Acts", f"{total_sadaqa}")

    st.subheader("Sibling Summary")
    summary = (
        df.groupby(["member", "kind"], as_index=False)["amount"]
        .sum()
        .pivot(index="member", columns="kind", values="amount")
        .fillna(0)
        .reset_index()
    )
    numeric_cols = [c for c in summary.columns if c != "member"]
    summary[numeric_cols] = summary[numeric_cols].astype(int)
    summary["Total"] = summary[numeric_cols].sum(axis=1)
    summary = summary.sort_values("Total", ascending=False)
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.subheader("Recent Activity")
    recent = df.copy()
    recent["created_at"] = pd.to_datetime(recent["created_at"], utc=True).dt.tz_convert(None)
    recent["created_at"] = recent["created_at"].dt.strftime("%Y-%m-%d %H:%M")
    recent = recent[["created_at", "member", "kind", "amount", "note"]].head(20)
    st.dataframe(recent, use_container_width=True, hide_index=True)

    st.caption("Tip: Set FAMILY_ACCESS_CODE and FAMILY_MEMBERS in Streamlit secrets before sharing the link.")


if __name__ == "__main__":
    main()
