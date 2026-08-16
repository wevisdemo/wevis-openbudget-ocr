from typing import List, Dict, Any
import os, json, re
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

def normalize_toc_data(toc_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    extracted_units = []
    latest_unit: Dict[str, Any] = {}
    for item_a, item_b in zip(toc_data, toc_data[1:]):

        # Check if either a unit or `7.` title
        title = item_a.get('title', '').strip()
        is_number_prefix = re.match(r"^[0-68-9]", title)
        if is_number_prefix: # if not; skip
            continue
        
        # Check if a unit or `7.` title
        if re.search(r"^7", title):
            extracted_units.append({
                'unit_title': latest_unit.get('title', None),
                'unit_page': latest_unit.get('page', None),
                'budget_page_start': item_a.get('page', ''),
                'budget_page_stop': item_b.get('page', '')
            })
            latest_unit = {}
            continue
        
        latest_unit = item_a
    
    return extracted_units
            

def extract_pdf_toc_to_json(pdf_dir_path: str, output_path: str) -> None:
    for filename in os.listdir(pdf_dir_path):
        if not filename.endswith(".pdf"):
            continue
        pdf_file = os.path.join(pdf_dir_path, filename)
        toc_data = extract_pdf_toc(pdf_file)
        normalized_toc_data = normalize_toc_data(toc_data)
        
        # Save to json
        json_output = json.dumps(normalized_toc_data, indent=4, ensure_ascii=False)
        output_json_path = os.path.join(output_path, filename.replace(".pdf", ".json"))
        with open(output_json_path, "w", encoding="utf-8") as f:
            f.write(json_output)