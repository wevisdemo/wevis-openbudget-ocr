import os
import json
import argparse
from thai_budget_extractor import extract_budget_object

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_dir", default="example/pdf", help="Path to directory contains pdf files")
    parser.add_argument("--toc_dir", default="output/toc", help="Output path for extracted Table of Content (json)")
    parser.add_argument("--tree_out", default="output/tree", help="Output path for extracted Budget Tree (csv)")
    parser.add_argument("--obj_out", default="output/obj", help="Output path for extracted Budget Object (json)")
    
    parser.add_argument("--overwrite", action="store_false", dest="skip_existing", 
                        help="Overwrite existing files instead of skipping them")
    parser.set_defaults(skip_existing=True)
    
    args = parser.parse_args()
    
    PDF_DIR_PATH = args.pdf_dir
    TOC_DIR_PATH = args.toc_dir
    TREE_OUTPATH = args.tree_out
    OBJ_OUTPATH = args.obj_out
    SKIP_EXISTING = args.skip_existing
    
    # Check and create output path
    os.makedirs(TOC_DIR_PATH, exist_ok=True)
    os.makedirs(TREE_OUTPATH, exist_ok=True)
    os.makedirs(OBJ_OUTPATH, exist_ok=True)
    
    # Extract budget data as object
    toc_files_list = sorted(os.listdir(TOC_DIR_PATH))
    for ministry_toc in toc_files_list:
        if not ministry_toc.endswith('.json'): continue
        ministry_name = ministry_toc.split(".")[0]
            
        json_output_file = os.path.join(OBJ_OUTPATH, f"{ministry_name}.json")
        csv_output_file = os.path.join(TREE_OUTPATH, f"{ministry_name}.csv")
        
        # Check if object is already processed; then skip
        if SKIP_EXISTING and os.path.exists(json_output_file):
            print(f"Skipping {ministry_name} (already exists)")
            continue
        
        with open(os.path.join(TOC_DIR_PATH, ministry_toc), "r") as f:
            toc_data = json.load(f)
        ministry = extract_budget_object(toc_data, pdf_dir=PDF_DIR_PATH)
        
        ministry_obj = ministry.to_dict()
        ministry_tree = ministry.get_budget_tree_df()
        
        # Save to json
        with open(json_output_file, "w", encoding="utf-8") as fj:
            json.dump(ministry_obj, fj, indent=4, ensure_ascii=False)
        # Save to csv
        ministry_tree.to_csv(csv_output_file, index=False)
    
if __name__ == "__main__":
    main()