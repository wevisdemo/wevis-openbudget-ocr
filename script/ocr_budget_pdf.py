import os
import json
import argparse
from toc_extractor import extract_pdf_toc_to_json
from thai_budget_extractor import extract_budget_object

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", default="example/pdf", help="Path to directory contains pdf files")
    parser.add_argument("--toc_out", default="output/toc", help="Output path for extracted Table of Content (json)")
    parser.add_argument("--tree_out", default="output/tree", help="Output path for extracted Budget Tree (csv)")
    parser.add_argument("--obj_out", default="output/obj", help="Output path for extracted Budget Object (json)")
    
    args = parser.parse_args()
    
    PDF_DIR_PATH = args.pdf_dir
    TOC_OUT_PATH = args.toc_out
    TREE_OUTPATH = args.tree_out
    OBJ_OUTPATH = args.obj_out
    
    # Check and create output path
    os.makedirs(TOC_OUT_PATH, exist_ok=True)
    os.makedirs(TREE_OUTPATH, exist_ok=True)
    os.makedirs(OBJ_OUTPATH, exist_ok=True)
    
    # Extract TOC data index
    extract_pdf_toc_to_json(PDF_DIR_PATH, TOC_OUT_PATH)
    
    # Extract budget data as object
    for ministry_toc in os.listdir(TOC_OUT_PATH):
        if not ministry_toc.endswith('.json'): continue
        with open(os.path.join(TOC_OUT_PATH, ministry_toc), "r") as f:
            toc_data = json.load(f)
            
        ministry = extract_budget_object(toc_data)
        ministry_obj = ministry.to_dict()
        ministry_tree = ministry.get_budget_tree()
        
        json_output_file = os.path.join(OBJ_OUTPATH, f"{ministry.ministry_name}.json")
        csv_output_file = os.path.join(TREE_OUTPATH, f"{ministry.ministry_name}.csv")
        
        # Save to json
        with open(json_output_file, "w", encoding="utf-8") as fj:
            json.dump(ministry_obj, fj, indent=4, ensure_ascii=False)
        # Save to csv
        ministry_tree.to_csv(csv_output_file, index=False)
        
    
if __name__ == "__main__":
    main()