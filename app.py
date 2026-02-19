from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "Tasbeeh Tracker"
DB_PATH = Path(__file__).parent / "data" / "tasbeeh_tracker.db"
REMINDERS = [
    "One small recitation today can be a lasting gift.",
    "Choose consistency over quantity. Add one good deed now.",
    "Recite, make dua, and log it with sincerity.",
    "A small sadaqa done regularly matters greatly.",
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
            member TEXT NOT NULL,
            type TEXT NOT NULL,
            count INTEGER NOT NULL,
            note TEXT
        )
        """
    )
    conn.commit()
    return conn


def add_entry(conn: sqlite3.Connection, member: str, typ: str, count: int, note: str) -> None:
    conn.execute(
        "INSERT INTO contributions (created_at, member, type, count, note) VALUES (?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), member, typ, count, note.strip() or None),
    )
    conn.commit()


def load_df(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT created_at, member, type, count, COALESCE(note,'') AS note FROM contributions ORDER BY created_at DESC",
        conn,
    )


def gate_access() -> None:
    code = st.secrets.get("FAMILY_ACCESS_CODE", "").strip()
    if not code:
        return
    entered = st.sidebar.text_input("Family access code", type="password")
    if entered != code:
        st.warning("Enter the family access code to continue.")
        st.stop()


def get_members() -> list[str]:
    raw = st.secrets.get("FAMILY_MEMBERS", "Sibling 1,Sibling 2,Sibling 3,Sibling 4")
    return [x.strip() for x in raw.split(",") if x.strip()]


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🤲", layout="wide")
    gate_access()

    st.title("Tasbeeh Tracker")
    st.caption("Family recitation and sadaqa tracker in memory of our father")

    if "ridx" not in st.session_state:
        st.session_state.ridx = 0

    c1, c2 = st.columns([6, 1])
    with c1:
        st.info(REMINDERS[st.session_state.ridx])
    with c2:
        if st.button("New"):
            st.session_state.ridx = (st.session_state.ridx + 1) % len(REMINDERS)
            st.rerun()

    conn = get_conn()
    members = get_members()

    with st.form("add"):
        col1, col2, col3 = st.columns(3)
        with col1:
            member = st.selectbox("Member", members + ["Other"])
            custom = st.text_input("Other name") if member == "Other" else ""
        with col2:
            typ = st.selectbox("Type", ["Recitation", "Sadaqa", "Dua", "Other Good Deed"])
        with col3:
            count = st.number_input("Count", min_value=1, max_value=1000, value=1, step=1)

        note = st.text_input("Note (optional)")
        submit = st.form_submit_button("Add Entry", use_container_width=True)

    if submit:
        name = custom.strip() if member == "Other" else member
        if not name:
            st.error("Please enter a name.")
        else:
            add_entry(conn, name, typ, int(count), note)
            st.success("Entry added.")

    df = load_df(conn)
    if df.empty:
        st.warning("No contributions yet.")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Total", int(df["count"].sum()))
    m2.metric("Recitations", int(df.loc[df["type"] == "Recitation", "count"].sum()))
    m3.metric("Sadaqa", int(df.loc[df["type"] == "Sadaqa", "count"].sum()))

    st.subheader("Sibling Summary")
    summary = df.groupby(["member", "type"], as_index=False)["count"].sum()
    pivot = summary.pivot(index="member", columns="type", values="count").fillna(0)
    pivot = pivot.astype(int)
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.reset_index().sort_values("Total", ascending=False)
    st.dataframe(pivot, use_container_width=True, hide_index=True)

    st.subheader("Recent Activity")
    recent = df.copy()
    recent["created_at"] = pd.to_datetime(recent["created_at"], utc=True).dt.strftime("%Y-%m-%d %H:%M UTC")
    st.dataframe(recent.head(20), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
