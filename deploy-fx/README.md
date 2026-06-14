# Deploy — FX Agent (public demo)

A lightweight, deployable version of the FX agent for a public URL. It reuses
`api-integration/agent_fx.py` and adds nothing heavy (no PyTorch), so it fits
free hosting tiers.

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (done).
2. Go to share.streamlit.io and sign in with GitHub.
3. New app, pick this repo, set the main file to `deploy-fx/app.py`.
4. In Advanced settings / Secrets, add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Deploy. You get a public URL.

The key is a secret in the host, never in the code. Locally the app reads it
from the repo-root `.env` instead.

## Run locally

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```
