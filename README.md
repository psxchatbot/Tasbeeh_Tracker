# Tasbeeh Tracker

Shared Streamlit app for 3-4 siblings to log recitation, sadaqa, dua, and good deeds.

## Run locally

```bash
cd /Users/nisar/Ammara/Github/family-sadaqa-counter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push this repo to GitHub.
2. Open https://share.streamlit.io and create a new app.
3. Select repo `psxchatbot/Tasbeeh_Tracker`, branch `main`, file `app.py`.
4. Add secrets:

```toml
FAMILY_ACCESS_CODE = "your-private-code"
FAMILY_MEMBERS = "Ammara,Ali,Sibling3,Sibling4"
```

## Note

SQLite file is stored in `data/tasbeeh_tracker.db`. On free hosting, data can reset after restarts; use Supabase for permanent cloud data.
