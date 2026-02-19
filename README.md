# Tasbeeh Tracker (Family)

A private family Streamlit app for collective deeds in memory of **Muhammad Ashraf**.

## Features

- Memorial opening message for your father
- Mobile-friendly layout
- One-time name save per device (cookie-based)
- Shared family code protection (optional)
- Collective counters only (no per-user public breakdown)
- Category logging tabs:
  - Tasbeeh
  - Zikr
  - Quran Recitation / Verses
  - Ahadith
  - Other Good Deeds
  - Sadaqah (PKR amount)
- Daily Islamic content:
  - Ayah of the Day
  - Hadith of the Day
  - Renowned Ahadith list
- In-app reminder settings per user

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
FAMILY_ACCESS_CODE = "your-private-code"
HADITH_API_KEY = "your-hadithapi-key"
# Optional override:
# HADITH_API_BASE_URL = "https://hadithapi.com/api"
```

## Notes

- SQLite DB path: `data/tasbeeh_tracker.db`
- Free Streamlit restarts may reset local file storage.
- For durable long-term data, migrate to Supabase/Postgres.
