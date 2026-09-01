# 📖 Detailed Usage Guide

This project provides a two-step pipeline to transform Thai Budget PDFs into structured data using `uv`. 

---

## 🔄 Extraction Workflow

To get the best results, you should run the tools in the following order:
1. **TOC Extraction**: Scans the PDF to create a digital map (Table of Contents).
2. **Budget OCR**: Uses that map to find and extract tabular data into CSV/JSON.

---

## 1. Table of Contents (TOC) Extraction

The `extract_toc.py` script parses the initial pages of the PDFs to identify the structure and page references for various ministries.

### Command
```bash
uv run python script/extract_toc.py --pdf_dir ./input_pdfs --toc_out ./output/toc
```

### Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--pdf_dir` | **(Required)** Path to the directory containing your source PDF files. | - |
| `--toc_out` | Path to the directory where the resulting JSON files will be saved. | `output/toc` |

**Note:** The script processes all PDFs found in the directory. Ensure your PDFs are not password-protected.

---

## 2. Budget Data Extraction

The `ocr_budget_pdf.py` script uses the TOC files generated in the previous step to navigate the PDF and perform OCR on the budget tables.

### Command
```bash
uv run python script/ocr_budget_pdf.py \
  --pdf_dir ./input_pdfs \
  --toc_dir ./output/toc \
  --tree_out ./output/tree \
  --obj_out ./output/obj
```

### Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--pdf_dir` | **(Required)** Path to the directory containing source PDF files. | - |
| `--toc_dir` | Path to the directory containing the TOC JSON files from Step 1. | `output/toc` |
| `--tree_out` | File path to save the extracted Budget Tree (Hierarchical CSV). | `output/tree` |
| `--obj_out` | File path to save the extracted Budget Object (Detailed JSON). | `output/obj` |

---

## 📂 Understanding the Outputs

### Budget Tree (`--tree_out`)
A **CSV file** optimized for spreadsheet tools (Excel/Google Sheets). It represents the budget hierarchy, showing the relationship between departments, projects, and allocated amounts. Intended for further validation.

### Budget Object (`--obj_out`)
A **JSON file** designed for developers and data analysts. It contains the raw metadata, and the full nested structure of the budget items.

---

## 💡 Troubleshooting

- **Empty TOC**: If the TOC extraction fails, verify that the PDF has a readable text layer. If it is a pure image scan, the TOC extractor may require specific OCR solution.
- **`uv run` updates**: If you have recently pulled changes from the repository, run `uv sync` to ensure your environment is up to date with the latest dependencies.
