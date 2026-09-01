# WeVis - Thailand's Budget OCR tools

Tools for processing and extracting data from Thai Budget PDF documents using OCR and structure analysis.

## 🚀 Quick Start

### 1. Prerequisites
You only need `uv` installed. It will automatically manage Python versions and virtual environments for you.

| Tool | Install Command |
| :--- | :--- |
| **uv** | `curl -LsSf https://astral.sh/uv/install.sh | sh` (or [see docs](https://docs.astral.sh/uv/getting-started/installation/)) |

### 2. Installation
Clone the repository and sync the dependencies:

```bash
git clone https://github.com/wevisdemo/wevis-openbudget-ocr.git
cd wevis-openbudget-ocr

# This creates a virtualenv and installs all local components (toc_extractor, etc.)
uv sync
```

## 📖 Usage

To start extracting data, you can run the scripts using `uv run`. 

For a complete list of commands, folder structures, and argument descriptions, please refer to our:
👉 **[Detailed Usage Guide](docs/USAGE.md)**

### Basic Example:
```bash
# 1. Extract Table of Contents
uv run python script/extract_toc.py --pdf_dir ./pdf

# 2. Extract Budget Data
uv run python script/ocr_budget_pdf.py --pdf_dir ./pdf
```
---

## 🛠 Development

This project uses `uv` workspaces. The core logic is split into local packages:
- `openbudget-toc-extractor`
- `openbudget-budget-extractor`

Because these are installed in **editable mode** (via `pyproject.toml`), any changes you make to the code in those folders will take effect immediately without needing to reinstall.

**Adding new dependencies:**
```bash
uv add package-name
```
