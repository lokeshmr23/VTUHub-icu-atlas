# ICU Atlas — research experimentation dashboard

A full-stack Flask + SQLite research workspace for **aggregate** comparative experiments in joint mortality and remaining ICU length-of-stay prediction. It includes session-based authentication, per-user resource isolation, dashboard and charts, full CRUD for datasets/models/experiments/qualitative notes, side-by-side quantitative comparison, research protocol guidance, responsive UI, seeded synthetic examples, empty states and optimistic create/edit/delete updates.

**This is a software demo, not a medical device or approved restricted-data platform.** It contains no MIMIC-IV or eICU patient records. All seeded metrics are **invented synthetic interface examples, not experimental findings**; do not quote them in any publication. Anyone with the preview URL can sign up and use the app: do not enter private or restricted information.

## Deploy on GitHub and Render

Follow [DEPLOY_RENDER.md](DEPLOY_RENDER.md) for commands customized to `lokeshmr23/VTUHub-icu-atlas` and both free-demo and durable-storage options. The root-level [`render.yaml`](render.yaml) supports New → Blueprint after it is pushed to the `main` branch. For paid Render persistent SQLite storage, attach a disk at `/var/data` and set `ICU_ATLAS_DATA_DIR=/var/data`. The free tier's local SQLite contents are ephemeral and can reset.

## Run locally

```bash
cd icuatlas
python -m pip install -r requirements.txt
python app.py
```

Open `http://localhost:8000`. The live preview in this workspace runs on port 8000, bound to `0.0.0.0`.

Demo login: `demo@icuatlas.app` / `demo1234`. Or register a new user for an empty workspace. SQLite data and the signing secret persist in `instance/`. For a deployment outside a local demo, replace the development server with a production WSGI setup, configure HTTPS, secure secret management, account recovery, audit logs and appropriate data-governance review. The demo credential must never be used in production.

## Research data pairing (proposal only)

- **Primary candidate:** MIMIC-IV v3.1, single-center US hospital/ICU EHR; credentialed access: https://physionet.org/content/mimiciv/3.1/
- **Secondary candidate:** eICU Collaborative Research Database v2.0, multi-center US ICU EHR; credentialed access: https://physionet.org/content/eicu-crd/2.0/

Only an authorized investigator should run analysis on each dataset, inside an approved environment. Harmonize the 24-hour landmark, inclusion criteria, unit of analysis, mortality endpoint, remaining ICU LoS in days, shared measurement and missingness definitions. Service/ward-based hyperedge families may differ between databases; do not claim the same structure is available without verification. Freeze preprocessing on development data and evaluate on eICU as a separate external test only after confirming comparable targets and permitted usage.

A defensible research comparison would contrast identical-information temporal baselines, a pairwise graph control and the proposed history-only hypergraph, using AUROC/AUPRC/Brier/calibration and LoS MAE/RMSE/R² with paired subject-level bootstrap intervals. Notes are designed to record qualitative failure modes (missingness, cold-start reference matching, workflow differences), not fabricated interview or clinical study findings. See the **Study protocol** tab in the app. No experiments were run as part of this build.

## API outline

- `POST /api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `GET /api/auth/me`
- `GET /api/bootstrap` — authenticated workspace snapshot
- `GET /api/{datasets|models|experiments|observations}`
- `POST /api/{resource}`, `GET/PATCH/DELETE /api/{resource}/{id}`

Session cookies are HttpOnly and SameSite=Lax; mutations require the CSRF token returned at login. Every CRUD route enforces ownership and validates aggregate metric ranges. Data is stored in SQLite; deleted referenced dataset/model records are blocked to protect experiment integrity. Auth and CRUD are functional; this is not a regulated system.

## Important restrictions

Do **not** upload raw MIMIC/eICU records, case narratives, restricted row-level model predictions, keys, or credentials to this app or this chat. The seeded dataset records are only **source configurations**, not the datasets themselves. PhysioNet's notice on restricted data and online/LLM services: https://physionet.org/news/post/llm-responsible-use/

See project journal documents in the workspace for earlier manuscript work. This application is intentionally separate from, and does not substantiate, any claimed research-paper results.
