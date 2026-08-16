from typing import List, Dict, Any
import os, json
import pymupdf

def extract_pdf_toc(
    pdf_path: str,
) -> List[Dict[str, Any]]:
    
    doc = pymupdf.open(pdf_path)
    # TODO: check for embeded toc data, if not found; use fallback to manual extraction
    toc = doc.get_toc()
    
    toc_data = [
        {"level": item[0], "title": item[1], "page": item[2]} 
        for item in toc
    ]
    
    return toc_data

def extract_pdf_toc_to_json(pdf_dir_path: str, output_path: str) -> None:
    for filename in os.listdir(pdf_dir_path):
        if not filename.endswith(".pdf"):
            continue
        pdf_file = os.path.join(pdf_dir_path, filename)
        toc_data = extract_pdf_toc(pdf_file)
        
        # Save to json
        json_output = json.dumps(toc_data, indent=4, ensure_ascii=False)
        output_json_path = os.path.join(output_path, filename.replace(".pdf", ".json"))
        with open(output_json_path, "w", encoding="utf-8") as f:
            f.write(json_output)