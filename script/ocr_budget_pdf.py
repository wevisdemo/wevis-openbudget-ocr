import os
from toc_extractor import extract_pdf_toc_to_json
from thai_budget_extractor import extract_budget_object

PDF_DIR_PATH = "example/pdf"
TOC_OUT_PATH = "output/toc"
TREE_OUTPATH = "output/tree"
OBJ_OUTPATH = "output/obj"

if __name__ == "__main__":
    
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