# FormoraReport

**English** | [**中文**](README.zh-CN.md)

Automated lab report generator for Windows — import a DOCX report template, experiment data, and materials (screenshots / source code / SQL / logs); it auto-detects fields, organizes content, generates charts, and inserts everything into the correct positions of the original template, exporting polished, editable **Word** and **PDF** reports.

> **No-AI mode is the default**: all core features work offline without any API key.
> **AI mode is optional**: enable it yourself and bring your own OpenAI-compatible API. Every generated value can be reviewed item by item.

---

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
- 👁 **Preview & validation**: catches missing fields before generation; preview, edit, and regenerate after
- 📤 **Export**: Word (`.docx`) by default; PDF via local LibreOffice or Microsoft Word (with honest fallback messages)
- 🌗 **Modern UI**: glassmorphism style, light/dark themes, high-DPI support
- 🔐 **Privacy-first**: everything stays local by default; AI keys are encrypted with Windows DPAPI, never stored in plaintext

## Operating Modes

| Capability | No-AI Mode (default) | AI Mode (optional) |
|------------|----------------------|--------------------|
| Template parsing / field mapping | ✅ | ✅ |
| Data processing / charts / batch / export | ✅ | ✅ |
| Semantic understanding of materials, drafting steps/results/conclusions | — | ✅ |
| Missing/contradiction checks | Basic validation | AI review |
| Works offline / without keys | ✅ Fully | — |
| Data sent to external API | Never | Only when you click "AI Assist" |

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

## License

This project is licensed under the **MIT License**. Third-party licenses are listed in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

Key dependencies: python-docx (MIT), docxtpl (LGPL-2.1), pdfplumber (MIT), openpyxl (MIT), pandas (BSD-3), matplotlib (PSF), PySide6 (LGPL-3), PyInstaller (GPL-2.0 with commercial exception).

## Contributing

Issues and Pull Requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) first.

## Roadmap

- OCR enhancement (optional PaddleOCR)
- Template center (save/manage common templates)
- Richer AI structured extraction with source-tracking visualization
- Installer (NSIS/Inno Setup) with auto-update
- More document format support

## Privacy

In No-AI mode all files are processed locally and nothing leaves your machine. In AI mode, content is sent to your configured API only when you explicitly trigger it. API keys are encrypted with Windows DPAPI. See [SECURITY.md](SECURITY.md) for details.