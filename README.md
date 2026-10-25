# FormoraReport

**English** | [**中文**](README.zh-CN.md)

Automated lab report generator for Windows — import a DOCX report template, experiment data, and materials (screenshots / source code / SQL / logs); it auto-detects fields, organizes content, generates charts, and inserts everything into the correct positions of the original template, exporting polished, editable **Word** and **PDF** reports.

> **No-AI mode is the default**: all core features work offline without any API key.
> **AI mode is optional**: enable it yourself and bring your own OpenAI-compatible API. Every generated value can be reviewed item by item.

---

## Downloads

Latest release: **v2.16.0**.

Grab the latest **single-file portable EXE** from the [Releases page](https://github.com/Liao0429/FormoraReport/releases). Every release ships a `FormoraReport.exe` asset — no Python installation required.

## Screenshots

*Liquid Glass UI · light mode*

![Light home](docs/screenshots/light_home.png)
![Light mapping](docs/screenshots/light_mapping.png)

*Dark mode*

![Dark home](docs/screenshots/dark_home.png)
![Dark mapping](docs/screenshots/dark_mapping.png)

*Template & generated report (rendered via LibreOffice)*

![Report template](docs/screenshots/template_p1.png)
![Generated report page 1](docs/screenshots/generated_report_p1.png)
![Generated report page 2](docs/screenshots/generated_report_p2.png)

## Features

- 📄 **DOCX template parsing**: detects `{{placeholders}}`, sections, tables, images, headers & footers
- 🔗 **Field mapping**: template placeholders ↔ data columns / constants / images, with auto-match + manual editing
- 📊 **Data processing**: reads CSV / XLSX / TXT / Markdown / PDF and auto-generates data charts
- 🖼 **Screenshot / image insertion**: inserts screenshots into the correct placeholder position
- ⚡ **Batch generation**: one template + many data rows → many reports at once
- 🧪 **Sample templates**: generic, physics (simple pendulum), and chemistry (HCl + marble) templates with matching CSV data — try them with one click
- 👁 **Preview & validation**: catches missing fields before generation; preview, edit, and regenerate after
- 📤 **Export**: Word (`.docx`) by default; PDF via local LibreOffice or Microsoft Word (with honest fallback messages)
- 🌗 **Modern UI**: glassmorphism style, light/dark themes, high-DPI support
- ⚡ **Non-blocking generation**: AI assist and batch generation run in background threads — the UI stays responsive
- 🛡 **Safety**: versioned outputs (never overwrite), SSRF-protected AI endpoint, image-path validation before generation
- 🔐 **Privacy-first**: everything stays local by default; a master **"Enable AI Assist"** switch can be turned off to guarantee zero network requests; AI keys are encrypted with Windows DPAPI, never stored in plaintext
- 🔄 **Auto-update check**: 3 seconds after launch, checks GitHub Releases in the background and asks before opening the download page; network failures stay silent
- 🐳 **Docker deployment**: one-command containerized REST API with LibreOffice + CJK fonts, rate limiting, and health checks

## Operating Modes

| Capability | No-AI Mode (default) | AI Mode (optional) |
|------------|----------------------|--------------------|
| Template parsing / field mapping | ✅ | ✅ |
| Data processing / charts / batch / export | ✅ | ✅ |
| Semantic understanding of materials, drafting steps/results/conclusions | — | ✅ |
| Missing/contradiction checks | Basic validation | AI review |
| Works offline / without keys | ✅ Fully | — |
| Data sent to external API | Never | Only when you click "AI Assist" |

> **Privacy switch**: in **Settings → AI Smart Mode**, "Enable AI Assist" is on by default. Turn it off to disable all AI configuration and guarantee the app never sends data anywhere — the AI client refuses to run before any network request.

## Windows Requirements

- Windows 10 / 11 (64-bit)
- No Python/Node development environment required (release package bundles the runtime)
- Optional: LibreOffice or Microsoft Word (for PDF export)
- Optional: an OpenAI-compatible API (`base_url` + `model` + key) for AI mode

## Installation & Usage

1. Unzip the release package and run `FormoraReport.exe`.
2. **Import documents**: choose a `.docx` lab report template (mark fill-in positions with `{{field}}` in Word), then choose experiment data (CSV/XLSX/TXT/MD/PDF).
3. Click **Parse template & data** and review the detected placeholders, sections, and tables.
4. **Field mapping**: verify auto-mapped fields; fill text fields directly, bind screenshots to fields whose names contain "screenshot"/"chart", and optionally check "auto-generate chart".
5. Click **Validate** to check missing fields, then **Generate report** or **Batch generate all rows**.
6. **Preview**: confirm content, then click **Export PDF** on the generate/preview page (requires LibreOffice or Word).
7. Optional: configure your API in **Settings → AI Smart Mode**, then click **✨ AI Assist** on the mapping page to let the model draft content from your materials.
8. **Auto-update**: the app checks GitHub Releases once, 3 seconds after launch. If a newer version exists, you are asked whether to open the Releases page; if the check fails (offline/timeout), nothing happens.

## Sample Templates

Built-in sample templates live in `tests/samples/` and are regenerated byte-for-byte by `scripts/make_samples.py`. The **"🎓 Try the sample template"** button on the home page loads the generic set instantly; the physics and chemistry sets showcase loops, auto charts, and image placeholders:

| Template | Experiment | Data file | Highlights |
|---|---|---|---|
| `实验报告模板.docx` | Generic experiment report | `实验数据.csv` | Loaded by the home-page sample button; bundled into the EXE (`samples/`) |
| `物理实验模板.docx` | Simple pendulum — measure gravitational acceleration `g` | `物理实验数据.csv` | `{{chart}}` auto chart, data-record loop, purpose/principle/procedure/error-analysis/conclusion sections |
| `化学实验模板.docx` | Dilute hydrochloric acid + marble (CaCO₃) | `化学实验数据.csv` | Image placeholder `{{装置图}}`, phenomenon-record loop, reagents/procedure/data-analysis sections |

## Build from Source

Prerequisites: **Python 3.14+** on Windows (developed and CI-tested on 3.14; 3.12+ should also work).

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/Scripts/activate          # Windows git-bash
# or .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py

# 4. Run tests
python -m pytest tests/ -q

# 5. Build the EXE
pyinstaller --noconfirm --clean --name FormoraReport --windowed \
  --collect-all matplotlib --collect-all docxtpl main.py
```

## REST API

FormoraReport ships a lightweight FastAPI server for headless / remote / mini-program integration. It exposes the same core pipeline (template parsing → data reading → mapping → generation → download → PDF → text extraction) over HTTP, and reports the current version (`2.16.0`) from `/api/health`.

**Start the server:**

```bash
pip install -r requirements-api.txt
python api_server.py --port 8000
```

- Interactive docs (Swagger UI): http://127.0.0.1:8000/docs
- Health check: `GET /api/health`

**Authentication (optional):** set the `FORMORA_API_KEY` environment variable to require a `Bearer` token on every endpoint except `/api/health`.

```bash
curl -H "Authorization: Bearer ***" http://127.0.0.1:8000/api/data/read
```

**Endpoints:**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check, version, cache/task counts, auth & rate-limit status (exempt from rate limiting) |
| `POST` | `/api/template/parse` | Upload a DOCX template → placeholders, sections, image slots |
| `POST` | `/api/data/read` | Upload data (CSV/XLSX/TXT/MD/PDF) → columns + preview rows |
| `POST` | `/api/image/upload` | Upload an image → `file_id` for image mappings |
| `POST` | `/api/mapping/auto` | Auto-match template placeholders ↔ data columns |
| `POST` | `/api/report/generate` | Generate a single DOCX report → `task_id` + download URL |
| `POST` | `/api/report/generate_batch` | Generate one DOCX per data row (JSON or multipart) |
| `GET` | `/api/report/{task_id}/download` | Download a generated report |
| `POST` | `/api/report/pdf` | Convert a generated DOCX to PDF |
| `POST` | `/api/report/{task_id}/text` | Extract report text (preview / AI review) |

**Batch generation — `POST /api/report/generate_batch`:**

Generates one report per data row and registers every output as a downloadable task (same TTL cleanup as single files). Accepts JSON or `multipart/form-data` (upload the data file directly).

```bash
# JSON mode
curl -H "Authorization: Bearer ***" -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8000/api/report/generate_batch -d '{
    "template_file_id": "tpl_...",
    "data_file_id": "data_...",
    "auto_chart": true,
    "mappings": [
      {"template_field": "姓名", "source_type": "column", "source_column": "姓名"}
    ]
  }'

# multipart mode (upload the data file)
curl -H "Authorization: Bearer ***" \
  -F "template_file_id=tpl_..." \
  -F 'mappings=[{"template_field":"姓名","source_type":"column","source_column":"姓名"}]' \
  -F "auto_chart=true" \
  -F "file=@实验数据.csv" \
  http://127.0.0.1:8000/api/report/generate_batch
```

Response: `total` / `generated` / `failed`, plus a `files` list with `file_name`, `task_id`, and `download_url`, and an `errors` list for failed rows.

> **Synchronous in v2.16.0**: the request blocks until all reports are generated — well suited for small/medium batches. An **asynchronous task-queue design** is documented as the next step: the endpoint would return `batch_id` (`202 Accepted`) and clients would poll `GET /api/report/batch/{batch_id}` for status and file lists.

**Rate limiting:** an in-memory sliding-window limiter allows **120 requests per minute per client IP** by default. Set `FORMORA_RATE_LIMIT` to override; requests above the limit get `429 Too Many Requests`. `/api/health` is exempt. The limiter is per-process (single worker) — use a shared store (e.g. Redis) or the bundled nginx config for multi-worker deployments.

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `FORMORA_API_KEY` | *(unset)* | Enables Bearer auth on all API endpoints except `/api/health` |
| `FORMORA_MAX_UPLOAD_MB` | `20` | Maximum upload size per file (MB) |
| `FORMORA_FILE_TTL_HOURS` | `1` | Hours before cached files/tasks expire |
| `FORMORA_MAX_CACHED_FILES` | `1000` | Max cached files before oldest are pruned |
| `FORMORA_RATE_LIMIT` | `120` | Max requests per minute per client IP (returns `429` above) |
| `FORMORA_CORS_ORIGINS` | `*` | Comma-separated allowed CORS origins |
| `TMPDIR` | `/data/tmp` (Docker) | Temp/upload directory; persisted via the data volume in Docker |

## Docker Deployment

The repository includes a production-oriented Docker setup for the REST API (`Dockerfile` + `docker-compose.yml` + optional `nginx.conf`).

```bash
# 1. (Recommended) set a strong API key in docker-compose.yml first
#    e.g. python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Build and start
docker compose up -d --build

# 3. Verify
curl http://127.0.0.1:8000/api/health
# {"status":"ok","version":"2.16.0","files_cached":0,"tasks":0,"auth_enabled":true,"rate_limit_per_minute":120}

# 4. Swagger UI
# http://127.0.0.1:8000/docs
```

Image details:

- Base: `python:3.12-slim`, runs as a **non-root** user (`formora`, uid 10001), `tini` as PID 1
- Bundles **LibreOffice** (headless DOCX→PDF / XLSX conversion) and **Noto CJK fonts** (Chinese charts & PDF rendering)
- Built-in `HEALTHCHECK` hitting `/api/health`; `docker-compose.yml` adds a data volume (`formora_data:/data`) and wires every environment variable (`FORMORA_API_KEY`, `FORMORA_MAX_UPLOAD_MB`, `FORMORA_FILE_TTL_HOURS`, `FORMORA_MAX_CACHED_FILES`, `FORMORA_RATE_LIMIT`, `FORMORA_CORS_ORIGINS`, `TMPDIR`)
- Optional [`nginx.conf`](nginx.conf): reverse proxy with per-IP rate limiting (`30r/m` + burst), `50m` client max body size, streaming downloads, and relaxed timeouts for long batch/PDF jobs

## Packaging

Build the single-file portable EXE with the checked-in PyInstaller spec:

```bash
python -m PyInstaller --noconfirm --clean FormoraReport-onefile.spec
```

The artifact is written to `dist/FormoraReport.exe` — double-click to run, no Python required.

## Tests

Run the full suite with:

```bash
python -m pytest tests/ -q
```

Test layout (all under `tests/`):

| File | Scope |
|------|-------|
| `test_core.py` | Integration: template parsing → data reading → mapping → generation → validation, using real sample files in `tests/samples/` |
| `test_config.py` | Config defaults, persistence, and DPAPI key encryption roundtrip |
| `test_models.py` | Unit tests for core data models (`TemplateInfo`, `DataSource`, `FieldMapping`, `ReportTask`) |
| `test_services.py` | Unit + integration for logging categories, history recording, and the report service (chart / single-generation) |
| `test_ai_client.py` | Offline tests for the AI client (URL building, payload, response parsing) with the HTTP layer mocked — no network needed |
| `test_ui.py` | Windows-only UI smoke test (runs `scripts/ui_smoke_test.py` headless) |

Guarantees:

- **No network**: every test is offline; AI-client tests mock the HTTP layer.
- **No private data**: tests use generated samples and write outputs to OS temp directories.
- **Repeatable**: sample files are regenerated only if missing; the suite is safe to run repeatedly.
- **Windows**: DPAPI encryption and the UI smoke test are Windows-specific; CI runs them on `windows-latest`.

## Tests & Known Limitations

- Automated tests cover core parsing/data/mapping/generation/validation/config encryption/UI smoke (`tests/`).
- PDF text extraction is reliable only for machine-generated PDFs; scanned documents require OCR (optional enhancement, not bundled).
- Legacy `.doc` files are not supported; save them as `.docx` in Word first.
- DOCX→PDF conversion depends on local LibreOffice or Word; when neither is available, only DOCX is exported with a clear message.

## Auto Update

After launch, FormoraReport checks GitHub Releases **once**, 3 seconds in, on a background thread. If a newer version exists, a dialog asks whether to open the Releases page; the check never blocks the UI, and network failures / timeouts / parse errors are silently ignored.

## License

This project is licensed under the **MIT License**. Third-party licenses are listed in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

Key dependencies: python-docx (MIT), docxtpl (LGPL-2.1), pdfplumber (MIT), openpyxl (MIT), pandas (BSD-3), matplotlib (PSF), PySide6 (LGPL-3), PyInstaller (GPL-2.0 with commercial exception).

## Contributing

Issues and Pull Requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first.

## Roadmap

- OCR enhancement (optional PaddleOCR)
- Template center (save/manage common templates)
- Richer AI structured extraction with source-tracking visualization
- Asynchronous batch API task queue (`batch_id` + status polling)
- Installer (NSIS/Inno Setup)
- More document format support

## Privacy

In No-AI mode all files are processed locally and nothing leaves your machine. A master switch, **Settings → AI Smart Mode → "Enable AI Assist"** (on by default), can be turned off to guarantee zero network requests — the AI client refuses to run before any upload, and the related settings/test button are disabled. In AI mode, content is sent to your configured API only when you explicitly trigger it. API keys are encrypted with Windows DPAPI. See [SECURITY.md](SECURITY.md) for details.
