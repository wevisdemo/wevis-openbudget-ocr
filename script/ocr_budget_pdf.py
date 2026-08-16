# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "PyMuPDF",
#     "toc_extractor",
# ]
# [tool.uv.sources]
# toc_extractor = { path = "../openbudget-toc-extractor", editable = true }
# ///

import os
from toc_extractor import extract_pdf_toc_to_json

PDF_DIR_PATH = "example/pdf"
TOC_OUT_PATH = "output/toc"

if __name__ == "__main__":
    
    # Check and create output path
    os.makedirs(TOC_OUT_PATH, exist_ok=True)
    
    # Craete TOC data index
    extract_pdf_toc_to_json(PDF_DIR_PATH, TOC_OUT_PATH)
    