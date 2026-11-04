# Mid-Cap Mutual Funds: The Cost of Investing

Seven-dashboard Dash app (Direct vs Regular plans), deployed on Render.

## Run locally
    pip install -r requirements.txt
    python app.py            # http://127.0.0.1:8050

## Production (Render)
    gunicorn app:server --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT

## Required files
    app.py
    requirements.txt
    data_collection/clean/nav_midcap_clean.parquet
    data_collection/clean/ter_midcap_clean.parquet
