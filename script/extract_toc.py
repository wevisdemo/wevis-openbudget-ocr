import os
import argparse
from toc_extractor import extract_pdf_toc_to_json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", required=True, help="Path to directory contains pdf files")
    parser.add_argument("--toc_out", default="output/toc", help="Output path for extracted Table of Content (json)")
    
    args = parser.parse_args()
    
    PDF_DIR_PATH = args.pdf_dir
    TOC_OUT_PATH = args.toc_out
    
    # Check and create output path
    os.makedirs(TOC_OUT_PATH, exist_ok=True)
    
    # Extract TOC
    extract_pdf_toc_to_json(PDF_DIR_PATH, TOC_OUT_PATH)
    
if __name__ == "__main__":
    main()