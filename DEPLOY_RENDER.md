# Push ICU Atlas to GitHub and deploy on Render

**Repository shown by the user:** https://github.com/lokeshmr23/VTUHub-icu-atlas (currently empty in the supplied screenshot). **App directory:** `/home/user/icuatlas` in this workspace. Push **this directory**, not `/home/user`: the parent contains private research-training certificates and other unrelated files.

## 1. Push the existing folder to GitHub

Run these commands in a terminal where this workspace is accessible:

```bash
cd /home/user/icuatlas
git status --short
# First configure your own Git name and email for this repository:
git config user.name "Your Name"
git config user.email "your-github-email@example.com"

git add .
git diff --cached --name-only
# Verify the list includes app.py, requirements.txt, render.yaml, static/,
# README.md, .gitignore and DEPLOY_RENDER.md,
# but NOT instance/, *.sqlite3 or flask-secret.txt.
git commit -m "Initial ICU Atlas dashboard with Render support"
git remote add origin https://github.com/lokeshmr23/VTUHub-icu-atlas.git
git push -u origin main
```

The project is already initialized with a `main` branch in this workspace. If `git remote add origin` says the remote already exists, use `git remote set-url origin https://github.com/lokeshmr23/VTUHub-icu-atlas.git` instead. If GitHub prompts for credentials, sign in using your own browser/credential manager or a personal access token; **do not send any credentials in chat**. If you downloaded the ZIP to your own computer, unzip it, `cd icuatlas`, then `git init -b main` before these commands. You can also upload the *unpacked source files* via GitHub's **uploading an existing file** option, but verify `.gitignore` is included and that files are at the repository root (not nested inside an extra directory). Do not upload the ZIP itself as the only file.

## 2. Deploy a free **demonstration** on Render

**If you opened New → Blueprint:** this repository now includes a root-level `render.yaml`. The error “Blueprint file render.yaml not found on main branch” means you must first commit and push `render.yaml` along with the app, then press **Retry** on the Blueprint page. The blueprint configures a Free Python web service, Gunicorn, `/healthz`, and a generated signing secret. Make sure the actual files are visible at the **top level of the `main` branch** on GitHub. This is a demo-only configuration: free SQLite storage is ephemeral. Do not create a second Web Service if you already deployed using Blueprint.

**Alternatively, configure manually without Blueprint:**

1. Visit https://dashboard.render.com/ and click **New → Web Service**.
2. Connect your GitHub account and select `lokeshmr23/VTUHub-icu-atlas`. If it does not show, grant Render access to this repository in GitHub's app permissions.
3. Use **Language: Python 3**, **Branch: main**, **Root directory: blank** (the project source is at repository root), **Build command:** `pip install -r requirements.txt`.
4. **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 90`.
5. **Health check path:** `/healthz` if Render offers a health-check setting.
6. Add a secret environment variable `ICU_ATLAS_SECRET`: generate a long random value on your own device with `python -c "import secrets; print(secrets.token_hex(40))"`. Do **not** put this value in GitHub or share it in chat. Leave `ICU_ATLAS_DATA_DIR` **unset** for a free demo.
7. Select the **Free** plan and deploy. Once it is Live, open the `https://<your-service>.onrender.com` URL. Use the public demo sign-in `demo@icuatlas.app` / `demo1234` to view synthetic data. Anyone who knows the demo password can edit the shared demo account; it is not a private research repository.

**Critical free-tier limitation:** this app currently uses **SQLite**. Render's free web services have an ephemeral filesystem: database records, new user accounts, and saved experiment summaries can disappear on redeploy, restart or spin-down. The free deployment is for showing the UI and functionality only, **not persistent research work**. The demo dataset will re-seed on startup. Setting the signing secret alone does not make SQLite persistent. Render's free service can also sleep when idle.

## 3. Keep accounts/results across Render restarts (paid persistent disk)

If you need actual persistent SQLite storage, choose a **paid Render web service** and attach a **persistent disk** with **mount path `/var/data`** (via **Advanced → Add disk** or service **Disks**), with a suitable size. Set `ICU_ATLAS_DATA_DIR=/var/data` in the service environment variables before using the app. Keep `ICU_ATLAS_SECRET` as a stable secret environment variable. Restart/redeploy after setting the disk and env var, and **create your actual accounts only after storage is mounted**. Data stored previously in the free ephemeral database will not automatically migrate.

An alternative is migrating the backend from SQLite to Postgres; this project does **not** support Postgres yet. Merely adding `DATABASE_URL` to Render will not work. Render's free Postgres instances also have limited lifespan; consult current pricing and retention before relying on one.

## 4. Security and scientific-integrity notes

- This is a demo, not a medical device or HIPAA/PhysioNet-approved processing environment. **Never enter or commit MIMIC/eICU patient-level data, restricted derivatives, credentials, or participant identifiers.** The demo scores are synthetic and cannot be cited as study results.
- Registration is open, the public demo login is intentionally shared, and rate limiting, email verification, account recovery and production monitoring are not included. Consider additional hardening before any serious multi-user use. The current code uses one Gunicorn worker to avoid concurrent SQLite initialization across workers.
- `.gitignore` excludes `instance/`, local secrets and common restricted-data formats. Before each push, inspect `git diff --cached --name-only` and `git status --short`.

Render docs: https://render.com/docs/deploy-flask ; https://render.com/docs/free ; https://render.com/docs/disks
