import os
import argparse
from toc_extractor import extract_pdf_toc_to_json
from thai_budget_extractor import extract_budget_object

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", default= "example/pdf", help="Path to directory contains pdf files")
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
    
    # Craete TOC data index
    extract_pdf_toc_to_json(PDF_DIR_PATH, TOC_OUT_PATH)
    
    # Extract budget
    for pdf_file in os.listdir(PDF_DIR_PATH):
        if not pdf_file.endswith(".pdf"):
            continue
        
        toc_file = pdf_file.replace(".pdf", ".json")
        # Load toc data
        import json
        with open(os.path.join(TOC_OUT_PATH, toc_file), "r") as f:
            toc_data = json.load(f)
        ministries = extract_budget_object(
            os.path.join(PDF_DIR_PATH, pdf_file),
            toc_data
        )
        
        for ministry in ministries:
            # Budget Tree
            # df = ministry.get_budget_tree()
            # df.to_csv(f"{ministry.ministry_name}.csv", index=False)
            
            # Dict
            ministry_obj = ministry.to_dict()
            with open(os.path.join(OBJ_OUTPATH, f"{ministry.ministry_name}.json"), "w") as fj:
                json.dump(ministry_obj, fj, indent=4, ensure_ascii=False)