# Tasbeeh Tracker (Family)

A shared Streamlit app for collective deeds in memory of **Muhammad Ashraf**.

## Features

- Memorial opening message for your father
- Mobile-friendly layout
- Glassmorphism UI (frosted cards, translucent layers)
- Open access (no login required)
- Collective counters only
- Deeds chart with quick +1 / +3 / +5 actions
- Separate Sadaqah tab with PKR tracking
- Front-page Ayat of the Day + Hadees of the Day
- Live API fetch with fallback content

## Local Run

```bash
cd /Users/nisar/Ammara/Github/family-sadaqa-counter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud Deploy

1. Push to GitHub repo.
2. In Streamlit Cloud, choose:
   - Repo: `psxchatbot/Tasbeeh_Tracker`
   - Branch: `main`
   - Main file: `app.py`
3. Add Secrets:

```toml
HADITH_API_KEY = "your-hadithapi-key"
# Optional override:
# HADITH_API_BASE_URL = "https://hadithapi.com/api"
```

## Notes

- SQLite DB path: `data/tasbeeh_tracker.db`
- Free Streamlit restarts may reset local file storage.
- For durable long-term data, migrate to Supabase/Postgres.
