from typing import List, Dict, Any
import os, json, re
import pymupdf
from .ministry_of_higer_education_handler import ministry_of_higer_edu_data_to_toc
from .province_group_handler import province_group_data_to_toc
from .lgo_handler import lgo_data_to_toc
from .unit_name_manager import UnitNameManager
from .working_capital_handler import convert_w_capital_data_to_toc

def adjust_toc_levels(data_list):
    # Find the index of the element where title is "สารบัญ"
    target_idx = -1
    for i, item in enumerate(data_list):
        if item.get("title") == "สารบัญ":
            target_idx = i
            break  # Stop at the first occurrence
            
    # Check if "สารบัญ" was found AND it's not the last element in the list
    if target_idx != -1 and target_idx + 1 < len(data_list):
        current_level = data_list[target_idx].get("level")
        next_level = data_list[target_idx + 1].get("level")
        
        # Check if the next element's level equals the "สารบัญ" level
        if current_level is not None and current_level == next_level:
            # Increment the level of EVERY element after "สารบัญ"
            for j in range(target_idx + 1, len(data_list)):
                if "level" in data_list[j]:
                    data_list[j]["level"] += 1
                    
    return data_list

def extract_pdf_toc(
    pdf_path: str,
) -> List[Dict[str, Any]]:
    
    doc = pymupdf.open(pdf_path)
    # TODO: check for embeded toc data, if not found; use fallback to manual extraction
    toc = doc.get_toc()
    
    absolute_path = os.path.abspath(pdf_path)
    filename = os.path.basename(absolute_path)
    
    toc_data = [
        {"level": item[0], "title": item[1], "doc": filename, "page": item[2]} 
        for item in toc
    ]
    
    toc_data = adjust_toc_levels(toc_data)
    
    # Add end doc buffer
    toc_data.append({
        "level": toc_data[-1].get('level', 3) + 1,
        "title": "999. end of doc",
        "doc": filename,
        "page": doc.page_count + 1,
    })
    
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
                'document': item_a.get('doc'),
                'unit_title': latest_unit.get('title', None),
                'unit_page': latest_unit.get('page', None),
                'budget_page_start': item_a.get('page', ''),
                'budget_page_stop': item_b.get('page', '')
            })
            latest_unit = {}
            continue
        
        latest_unit = item_a
    
    return extracted_units

def convert_toc_data_to_toc(
    toc_data: List[Dict[str, Any]],
    ministries_toc: Dict[str, Any], 
    filename: str
):
    
    toc_level = None
    last_ministry = None
    last_unit = None
    for item_id, item in enumerate(toc_data):
        if item.get('title') == 'สารบัญ':
            toc_level = item.get('level')
            continue
        if toc_level is None: continue # skip until found สารบัญ
        
        title = item.get('title', '0')
        current_lvl = item.get('level', 21)
        doc = item.get('doc', '')
        page = item.get('page', 0)
        if not re.search(r"^\d", title): # found name
            if current_lvl <= toc_level + 1:
                # is ministry
                if last_ministry:
                    # Check and add last unit
                    if last_unit:
                        last_ministry['budgetary_units'].append(last_unit)
                    ministry_name = last_ministry.get('name', '').strip()
                    ministries_toc[ministry_name] = last_ministry
                last_ministry = {
                    'name': UnitNameManager.get_ministry_name(title).strip(),
                    'document': doc,
                    'unit_page': page,
                    'budgetary_units': []
                }
                last_unit = None # reset unit for new ministry
                continue
            # is budgetary unit
            elif last_unit and last_ministry:
                last_ministry['budgetary_units'].append(last_unit)
                title = UnitNameManager.get_unit_name(
                    title
                ).strip()
            last_unit = {
                'name': title,
                'document': doc,
                'unit_page': page,
            }
        # Check 7.
        if re.search(r"^7\.", title): # found budget plan
            if last_unit:
                last_unit['budget_page_start'] = page
                last_unit['budget_page_stop'] = toc_data[item_id+1].get('page')
        # Handle งบกลาง
        if re.search(r"^3\. รายละเอียดงบ", title) \
            and last_ministry and last_ministry.get('name') == 'งบกลาง': # found budget plan
                last_ministry['budget_page_start'] = page
                last_ministry['budget_page_stop'] = toc_data[item_id+1].get('page')
            
    if last_unit and last_ministry:
        last_ministry['budgetary_units'].append(last_unit)
        ministries_toc[last_ministry.get('name', '').strip()] = last_ministry

def extract_pdf_toc_to_json(
    pdf_dir_path: str, 
    output_path: str,
    normalize: bool=True
) -> None:

    ministries_toc = {}
    for filename in os.listdir(pdf_dir_path):
        if not filename.endswith(".pdf"):
            continue
        pdf_file = os.path.join(pdf_dir_path, filename)
        toc_data = extract_pdf_toc(pdf_file)
        if any('กลุ่มจังหวัด' in _title for _title in [toc_data[_].get('title', '') for _ in range(5)]):
            province_group_data_to_toc(toc_data, ministries_toc, filename)
        elif any('อุดมศึกษา' in _title for _title in [toc_data[_].get('title', '') for _ in range(5)]):
            ministry_of_higer_edu_data_to_toc(toc_data, ministries_toc, filename)
        elif any('ส่วนท้องถิ่น' in _title for _title in [toc_data[_].get('title', '') for _ in range(5)]):
            lgo_data_to_toc(toc_data, ministries_toc, filename)
        elif any('ทุนหมุนเวียน' in _title for _title in [toc_data[_].get('title', '') for _ in range(len(toc_data))]):
            convert_w_capital_data_to_toc(toc_data, ministries_toc, filename)
        else:
            convert_toc_data_to_toc(toc_data, ministries_toc, filename)
         
    # Split data to ministry level
    for ministry, toc in ministries_toc.items():
        if re.search(r"^แผนงาน", ministry): # skip แผนงาน
            continue
        with open(os.path.join(output_path, f"{ministry}.json"), "w") as f:
            json.dump(toc, f, indent=4, ensure_ascii=False)
                    