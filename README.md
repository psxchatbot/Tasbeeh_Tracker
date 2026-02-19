# Family Sadaqa & Recitation App

A shared family app to log recitations, sadaqa, dua, and other good deeds in memory of your father.

## What changed

- Upgraded from local browser-only counter to a shared Streamlit app
- Better design for mobile + desktop
- Sibling summary table and recent activity feed
- Optional family access code

## Local run

```bash
cd /Users/nisar/Ammara/Github/family-sadaqa-counter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push this repo to GitHub.
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Create app from your repo:
   - Main file path: `app.py`
4. In app settings, add secrets:

```toml
FAMILY_ACCESS_CODE = "your-private-code"
FAMILY_MEMBERS = "Ammara,Ali,Sibling3,Sibling4"
```

5. Deploy and share the link only with family.

## Important note about storage

- This version uses SQLite (`/data/family_counter.db`).
- On some free hosting restarts, data may reset.
- For durable long-term storage, next step is moving data to Supabase.

## Next upgrade options

- Supabase backend for durable data
- Individual login per sibling
- Monthly goals and notification reminders
- Android/iOS app wrapper later
