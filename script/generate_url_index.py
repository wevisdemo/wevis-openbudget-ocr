import os, re
import json
import argparse
import pandas as pd
from toc_extractor import extract_pdf_toc_to_json

PDF_BASE_URL = "https://bbstore.bb.go.th/cms/"

def thai_to_arabic(text: str) -> str:
    thai_digits = "๐๑๒๓๔๕๖๗๘๙"
    arabic_digits = "0123456789"

    trans_table = str.maketrans(thai_digits, arabic_digits)

    result = text.translate(trans_table)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", required=True, help="Path to directory contains pdf files")
    parser.add_argument("--toc_out", default="output/toc", help="Output path for extracted Table of Content (json)")
    parser.add_argument("--url_index_out", default="output/url_index", help="Output path for extracted Table of Content (json)")
    parser.add_argument("--drafted", action="store_true", dest="is_drafted", 
        help="Mark whether the budget pdf is drafed version")
    
    args = parser.parse_args()
        
    PDF_DIR_PATH = args.pdf_dir
    TOC_OUT_PATH = args.toc_out
    URL_INDX_OUT_PATH = args.url_index_out
    IS_DRAFTED = args.is_drafted
    
    os.makedirs(TOC_OUT_PATH, exist_ok=True)
    os.makedirs(URL_INDX_OUT_PATH, exist_ok=True)
    
    # Extract TOC data index
    extract_pdf_toc_to_json(PDF_DIR_PATH, TOC_OUT_PATH)
    
    # Load doc URL index
    with open(os.path.join(PDF_DIR_PATH, "doc_url_index.json"), "r") as f:
        doc_url = json.load(f)
    url_index = {
        d['pdf_filename']: d['url'] for d in doc_url
    }
    doc_title_index = {
        d['pdf_filename']: d['doc_title'] for d in doc_url
    }
    # Extract budget year
    budget_year = 'NAN'
    budget_year_match = re.search(r"พ\.ศ\.\s?(\d{4})", doc_url[0].get('doc_title', ''))
    if budget_year_match:
        budget_year = thai_to_arabic(budget_year_match.group(1))
        if IS_DRAFTED:
            budget_year += "_drafted"
        
    # Create URL index
    data = []
    for minitry_filename in os.listdir(TOC_OUT_PATH):
        if not minitry_filename.endswith('.json'):
            continue
        with open(os.path.join(TOC_OUT_PATH, minitry_filename), "r") as f:
            ministry = json.load(f)
            
        data.append({
            'MINISTRY': ministry.get('name'),
            'BUDGETARY_UNIT': ministry.get('name'),
            'PDF_NAME': doc_title_index.get(ministry.get('document')),
            'PDF_URL': url_index.get(ministry.get('document')),
            'PAGE_URL': f"{PDF_BASE_URL}{ministry.get('document')}?#page={ministry.get('unit_page')}",
        })
        for budgetary_unit in ministry.get('budgetary_units'):
            if not budgetary_unit:
                continue
            data.append({
                'MINISTRY': ministry.get('name'),
                'BUDGETARY_UNIT': budgetary_unit.get('name'),
                'PDF_NAME': doc_title_index.get(budgetary_unit.get('document')),
                'PDF_URL': url_index.get(budgetary_unit.get('document')),
                'PAGE_URL': f"{PDF_BASE_URL}{budgetary_unit.get('document')}?#page={budgetary_unit.get('unit_page')}",
            })
        
    df = pd.DataFrame(data)
    # Add BUDGET_YEAR
    df.insert(0, 'BUDGET_YEAR', [budget_year for _ in range(len(df.index))])
    df.to_csv(os.path.join(URL_INDX_OUT_PATH, f'sourceURL_{budget_year}.csv'), index=False)

if __name__ == "__main__":
    main()