# Third-Party Notices

Generated on **2026-10-26** for the **FormoraReport** project.

This document lists the third-party open-source packages that FormoraReport depends on, both directly and transitively. The list was produced from the project's Python virtual environment (`.venv`) with `pip freeze`, and license information was retrieved from each package's installed distribution metadata (`importlib.metadata`) and cross-checked against PyPI where metadata was missing. Version numbers match the exact pinned versions installed in the environment.

## Copyleft / viral-license notice

The following packages use **copyleft licenses (GPL family)**. If you distribute FormoraReport or a modified/derivative version of it, these licenses impose conditions on how you may license and share the combined work:

| Package | Version | License | Implication |
|---|---|---|---|
| docxtpl | 0.20.2 | LGPL-2.1-only | Weak copyleft. Linking is generally permitted; modifications to the library itself must be released under LGPL-2.1. |
| PySide6_Essentials | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Weak copyleft (LGPL option). Dynamic linking is allowed under LGPL terms; you may also choose the GPL terms. |
| shiboken6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Weak copyleft (LGPL option); binding generator for PySide6. |
| pyinstaller | 6.22.3 | GPL-2.0-or-later WITH PyInstaller exception | Copyleft with a special exception that explicitly permits bundling and distributing non-free/commercial applications built with PyInstaller. |
| pymupdf | 2.0 | AGPL-3.0 OR Commercial | Strong copyleft. Derivative works distributed to third parties must be licensed under AGPL-3.0, or you must obtain a commercial license from Artifex. |
| pymupdf4llm | 2.0 | AGPL-3.0 OR Commercial | Same license as pymupdf (empty transition package; functionality merged into pymupdf 2.x). |
| pymupdf_layout | 2.0 | AGPL-3.0 OR Commercial | Same license as pymupdf (empty transition package; functionality merged into pymupdf 2.x). |

**MPL-2.0** (`certifi`, `pathspec`) is a file-level copyleft license: modifications to the MPL-licensed files must be made available under MPL-2.0, but the rest of the application is not affected. This is generally considered safe for proprietary distribution when the MPL files are used unmodified.

## Package list

| Package | Version | License | Description |
|---|---|---|---|
| altgraph | 0.17.5 | MIT | Python graph (network) package |
| annotated-types | 0.8.0 | MIT | Reusable constraint types to use with typing.Annotated |
| anyio | 4.15.1 | MIT | High-level concurrency and networking framework on top of asyncio or Trio |
| ast_serialize | 0.13.1 | MIT | Python bindings for mypy AST serialization |
| boolean.py | 5.0 | BSD-2-Clause | Define boolean algebras, create and parse boolean expressions and create custom boolean DSL. |
| CacheControl | 0.14.4 | Apache-2.0 | httplib2 caching for requests |
| certifi | 2026.10.23 | MPL-2.0 | Python package for providing Mozilla's CA Bundle. |
| cffi | 2.1.1 | MIT-0 | Foreign Function Interface for Python calling C code. |
| charset-normalizer | 3.5.2 | MIT | The Real First Universal Charset Detector. Open, modern and actively maintained alternative to Chardet. |
| click | 8.5.0 | BSD-3-Clause | Composable command line interface toolkit |
| colorama | 0.4.6 | BSD-3-Clause | Cross-platform colored terminal text. |
| contourpy | 1.4.0 | BSD-3-Clause | Python library for calculating contours of 2D quadrilateral grids |
| coverage | 7.17.0 | Apache-2.0 | Code coverage measurement for Python |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | cryptography is a package which provides cryptographic recipes and primitives to Python developers. |
| cycler | 0.12.1 | BSD-3-Clause | Composable style cycles |
| cyclonedx-python-lib | 11.12.0 | Apache-2.0 | Python library for CycloneDX |
| defusedxml | 0.7.1 | PSF-2.0 | XML bomb protection for Python stdlib modules |
| docxtpl ⚠️ | 0.20.2 | LGPL-2.1-only | Python docx template engine |
| et_xmlfile | 2.0.0 | MIT | An implementation of lxml.xmlfile for the standard library |
| fastapi | 0.115.6 | MIT | FastAPI framework, high performance, easy to learn, fast to code, ready for production |
| filelock | 4.2.4 | MIT | A platform independent file lock. |
| flatbuffers | 25.12.19 | Apache-2.0 | The FlatBuffers serialization format for Python |
| fonttools | 4.67.0 | MIT | Tools to manipulate font files |
| git-filter-repo | 2.47.0 | MIT | Quickly rewrite git repository history |
| h11 | 0.16.0 | MIT | A pure-Python, bring-your-own-I/O implementation of HTTP/1.1 |
| httpcore | 1.0.9 | BSD-3-Clause | A minimal low-level HTTP client. |
| httptools | 0.9.0 | MIT | A collection of framework independent HTTP protocol utils. |
| httpx | 0.27.2 | BSD-3-Clause | The next generation HTTP client. |
| idna | 3.20 | BSD-3-Clause | Internationalized Domain Names in Applications (IDNA) |
| iniconfig | 2.3.1 | MIT | brain-dead simple config-ini parsing |
| Jinja2 | 3.1.6 | BSD-3-Clause | A very fast and expressive template engine. |
| kiwisolver | 1.5.1 | BSD-3-Clause | A fast implementation of the Cassowary constraint solver |
| librt | 0.16.0 | MIT | Mypyc runtime library |
| license-expression | 30.4.4 | Apache-2.0 | license-expression is a comprehensive utility library to parse, compare, simplify and normalize license expressions (such as SPDX license expressions) using boolean logic. |
| lxml | 6.1.3 | BSD-3-Clause | Powerful and Pythonic XML processing library combining libxml2/libxslt with the ElementTree API. |
| markdown-it-py | 4.2.0 | MIT | Python port of markdown-it. Markdown parsing, done right! |
| MarkupSafe | 3.0.4 | BSD-3-Clause | Safely add untrusted strings to HTML/XML markup. |
| matplotlib | 3.11.2 | Matplotlib License (BSD-style) | Python plotting package |
| mdurl | 0.1.2 | MIT | Markdown URL utilities |
| msgpack | 1.2.3 | Apache-2.0 | MessagePack serializer |
| mypy | 2.4.0 | MIT | Optional static typing for Python |
| mypy_extensions | 1.1.0 | MIT | Type system extensions for programs checked with the mypy type checker. |
| networkx | 3.7 | BSD-3-Clause | Python package for creating and manipulating graphs and networks |
| numpy | 2.5.4 | BSD-3-Clause (bundled components: 0BSD, MIT, Zlib, CC0-1.0) | Fundamental package for array computing in Python |
| onnxruntime | 1.31.0 | MIT | ONNX Runtime is a runtime accelerator for Machine Learning models |
| openpyxl | 3.1.5 | MIT | A Python library to read/write Excel 2010 xlsx/xlsm files |
| packageurl-python | 0.17.6 | MIT | A purl aka. Package URL parser and builder |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Core utilities for Python packages |
| pandas | 3.1.0 | BSD-3-Clause | Powerful data structures for data analysis, time series, and statistics |
| pathspec | 1.1.1 | MPL-2.0 | Utility library for gitignore style pattern matching of file paths. |
| pdfminer.six | 20260107 | MIT | PDF parser and analyzer |
| pdfplumber | 0.11.10 | MIT | Plumb a PDF for detailed information about each char, rectangle, and line. |
| pefile | 2024.8.26 | MIT | Python PE parsing module |
| pillow | 13.0.0 | MIT-CMU (PIL License) | Python Imaging Library (fork) |
| pip-requirements-parser | 32.0.1 | MIT | pip requirements parser - a mostly correct pip requirements parsing library because it uses pip's own code. |
| pip_api | 0.0.35 | Apache-2.0 | An unofficial, importable pip API |
| pip_audit | 2.10.1 | Apache-2.0 | A tool for scanning Python environments for known vulnerabilities |
| platformdirs | 4.13.5 | MIT | A small Python package for determining appropriate platform-specific dirs, e.g. a `user data dir`. |
| pluggy | 1.7.0 | MIT | plugin and hook calling mechanisms for python |
| protobuf | 7.36.2 | BSD-3-Clause | Protocol Buffers runtime library (Google's data interchange format). |
| psutil | 7.2.2 | BSD-3-Clause | Cross-platform lib for process and system monitoring. |
| py-serializable | 2.1.0 | Apache-2.0 | Library for serializing and deserializing Python Objects to and from JSON and XML. |
| pycparser | 3.12 | BSD-3-Clause | C parser in Python |
| pydantic | 2.14.1 | MIT | Data validation using Python type hints |
| pydantic_core | 2.50.1 | MIT | Core functionality for Pydantic validation and serialization |
| pyflakes | 4.0.3 | MIT | passive checker of Python programs |
| Pygments | 2.21.0 | BSD-2-Clause | Pygments is a syntax highlighting package written in Python. |
| pyinstaller ⚠️ | 6.22.3 | GPL-2.0-or-later WITH PyInstaller exception | PyInstaller bundles a Python application and all its dependencies into a single package. |
| pyinstaller-hooks-contrib | 2026.9 | Apache-2.0 | Community maintained hooks for PyInstaller |
| pymupdf ⚠️ | 2.0 | AGPL-3.0 OR Commercial | A high performance Python library for data extraction, analysis, conversion & manipulation of PDF (and other) documents. |
| pymupdf4llm ⚠️ | 2.0 | AGPL-3.0 OR Commercial (empty transition package; code merged into pymupdf) | Empty transition package required by pymupdf 2.x; the 4llm (LLM helper) code is now part of pymupdf. |
| pymupdf_layout ⚠️ | 2.0 | AGPL-3.0 OR Commercial (empty transition package; code merged into pymupdf) | Empty transition package required by pymupdf 2.x; the layout-analysis code is now part of pymupdf. |
| pyparsing | 3.3.3 | MIT | pyparsing - Classes and methods to define and execute parsing grammars |
| pypdfium2 | 5.14.0 | BSD-3-Clause (Apache-2.0 for bundled third-party code) | Python bindings to PDFium |
| PySide6_Essentials ⚠️ | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Python bindings for the Qt cross-platform application and UI framework (Essentials) |
| pytest | 9.1.1 | MIT | pytest: simple powerful testing with Python |
| pytest-cov | 7.1.0 | MIT | Pytest plugin for measuring coverage. |
| python-dateutil | 3.0.0 | Apache-2.0 OR BSD-3-Clause | Extensions to the standard Python datetime module |
| python-docx | 1.2.0 | MIT | Create, read, and update Microsoft Word .docx files. |
| python-dotenv | 1.2.4 | BSD-3-Clause | Read key-value pairs from a .env file and set them as environment variables |
| python-multipart | 0.0.20 | Apache-2.0 | A streaming multipart parser for Python |
| pywin32 | 312 | PSF-2.0 | Python for Windows Extensions |
| pywin32-ctypes | 0.2.3 | BSD-3-Clause | A (partial) reimplementation of pywin32 using ctypes/cffi |
| PyYAML | 6.0.3 | MIT | YAML parser and emitter for Python |
| requests | 2.34.2 | Apache-2.0 | Python HTTP for Humans. |
| rich | 15.0.0 | MIT | Render rich text, tables, progress bars, syntax highlighting, markdown and more to the terminal |
| ruff | 0.17.2 | MIT | An extremely fast Python linter and code formatter, written in Rust. |
| setuptools | 84.2.1 | MIT | Most extensible Python build backend with support for C/C++ extension modules |
| shiboken6 ⚠️ | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Python/C++ bindings helper module |
| six | 1.17.0 | MIT | Python 2 and 3 compatibility utilities |
| sniffio | 1.3.1 | MIT OR Apache-2.0 | Sniff out which async library your code is running under |
| sortedcontainers | 2.4.0 | Apache-2.0 | Sorted Containers -- Sorted List, Sorted Dict, Sorted Set |
| starlette | 0.41.3 | BSD-3-Clause | The little ASGI library that shines. |
| tabulate | 0.10.0 | MIT | Pretty-print tabular data |
| tomli | 2.5.0 | MIT | A lil' TOML parser |
| tomli_w | 1.2.0 | MIT | A lil' TOML writer |
| typing-inspection | 0.4.4 | MIT | Runtime typing introspection tools |
| typing_extensions | 4.16.0 | PSF-2.0 | Backported and Experimental Type Hints for Python 3.9+ |
| tzdata | 2026.5 | Apache-2.0 | Provider of IANA time zone data |
| urllib3 | 2.8.0 | MIT | HTTP library with thread-safe connection pooling, file post, and more. |
| uvicorn | 0.34.0 | BSD-3-Clause | The lightning-fast ASGI server. |
| watchfiles | 1.3.0 | MIT | Simple, modern and high performance file watching and code reload in python. |
| websockets | 17.3 | BSD-3-Clause | An implementation of the WebSocket Protocol (RFC 6455 & 7692) |

## Notes

- License names above are abbreviated (SPDX-style) and were taken from package metadata (`License` / `License-Expression` fields, `License ::` trove classifiers) or, when unavailable, from the package's PyPI record.
- Several packages are dual- or multi-licensed (e.g. `PySide6_Essentials`, `pymupdf`, `python-dateutil`, `cryptography`, `sniffio`, `packaging`). You may choose the applicable license according to each project's terms.
- `matplotlib` is distributed under its own BSD-style license agreement; `pillow` under the MIT-CMU (PIL) license; `pywin32` and `defusedxml` under the Python Software Foundation License (PSF-2.0).
- This list is informational. For legal distribution, please review the actual `LICENSE` / `COPYING` files shipped inside each installed package (`site-packages`) and consult the corresponding upstream project pages.
