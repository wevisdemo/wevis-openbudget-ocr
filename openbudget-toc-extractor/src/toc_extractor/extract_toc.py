from typing import List, Dict, Any
import os, json, re
from pathlib import Path
import pymupdf
from .constants import MINISTRY_NAMES

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
            
def convert_to_pattern(text: str) -> str:
    pttn_text = re.sub(r"\s", r"\\s\?", text)
    return r"^" + pttn_text

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
        if item.get('level') == toc_level + 1: # ministry
            # Clean ministry name
            ministry_name = item.get('title', '')
            if last_ministry:
                clean_ministry_name = re.sub(r"\(.*\)", "", last_ministry.get('name', '')).strip()
                # Check if already had ts ministry
                if clean_ministry_name in ministries_toc:
                    ministries_toc[clean_ministry_name]['budgetary_units'].extend(last_ministry['budgetary_units'])
                    if re.search(r"\((.+)?1(.+)?\)", last_ministry.get('name', '')):
                        ministries_toc[clean_ministry_name]['name'] = clean_ministry_name
                        ministries_toc[clean_ministry_name]['document'] = filename
                        ministries_toc[clean_ministry_name]['unit_page'] = item.get('page')
                        
                else:
                    # check for left over unit
                    if last_unit:
                        last_ministry['budgetary_units'].append(last_unit)
                    ministries_toc[clean_ministry_name] = last_ministry # Add mnistry
            
            # new ministry
            last_ministry = {
                'name': ministry_name,
                'document': filename,
                'unit_page': item.get('page'),
                'budgetary_units': []
            }
            last_unit = None
            
        elif item.get('level') == toc_level + 2: # sub item from ministry
            unit_name = item.get('title', '0')
            # TODO: check for รายการงบ
            if re.search(r"^\d", unit_name):
                continue
            if last_unit and last_ministry:
                last_ministry['budgetary_units'].append(last_unit)
            last_unit = {
                'name': unit_name,
                'document': filename,
                'unit_page': item.get('page'),
                'budget_page_start': None,
                'budget_page_stop': None,
            }
        elif item.get('level') == toc_level + 3: # budget
            detail_header = item.get('title', '')
            if last_unit and re.search(r"7\.", detail_header):
                last_unit['budget_page_start'] = item.get('page')
                last_unit['budget_page_stop'] = toc_data[item_id+1].get('page')
    
    # Add the last ministry                    
    if last_ministry:
        clean_ministry_name = re.sub(r"\(.*\)", "", last_ministry.get('name', '')).strip()
        last_ministry['name'] = clean_ministry_name
        if last_unit:
            last_ministry['budgetary_units'].append(last_unit)
            
        # Check if already had ts ministry
        if ministry_name in ministries_toc:
            ministries_toc[clean_ministry_name]['budgetary_units'].extend(last_ministry['budgetary_units'])
        else:
            ministries_toc[clean_ministry_name] = last_ministry # Add mnistry
    
def convert_province_data_to_toc(
    toc_data: List[Dict[str, Any]], 
    ministries_toc: Dict[str, Any], 
    filename: str
):
    
    toc_level = None
    last_unit = None
    
    last_ministry = ministries_toc.get('จังหวัดและกลุ่มจังหวัด', None)
    if last_ministry is None:
        last_ministry = {
            'name': 'จังหวัดและกลุ่มจังหวัด',
            "document": None,
            "unit_page": None,
            "budgetary_units": []
        }
        
    for item_id, item in enumerate(toc_data):
        if item.get('title') == 'สารบัญ':
            toc_level = item.get('level')
            continue
        if toc_level is None: continue # skip until found สารบัญ
        if item.get('level') == toc_level + 1: # ministry
            # Clean ministry name
            ministry_name = item.get('title', '')
            if re.search(r"1", ministry_name): # found first doc
                last_ministry['unit_page'] = item.get('page')
                last_ministry['document'] = filename
                
        elif item.get('level') == toc_level + 2: # province group
            unit_name = item.get('title', '0')
            if re.search(r"^\d", unit_name):
                continue
            if last_unit and last_ministry:
                last_ministry['budgetary_units'].append(last_unit)
            last_unit = {
                'name': unit_name,
                'document': filename,
                'unit_page': item.get('page'),
                'budget_page_start': None,
                'budget_page_stop': None,
            }
        elif item.get('level') == toc_level + 3:
            detail_header = item.get('title', '0')
            if last_unit and re.search(r"7\.", detail_header):
                last_unit['budget_page_start'] = item.get('page')
                last_unit['budget_page_stop'] = toc_data[item_id+1].get('page')
                continue
            if last_unit and re.search(r"^จังหวัด", detail_header):
                last_ministry['budgetary_units'].append(last_unit)
                # Initiate new unit
                last_unit = {
                    'name': detail_header,
                    'document': filename,
                    'unit_page': item.get('page'),
                    'budget_page_start': None,
                    'budget_page_stop': None,
                }
        elif item.get('level') == toc_level + 4:
            detail_header = item.get('title', '0')
            if last_unit and re.search(r"7\.", detail_header):
                last_unit['budget_page_start'] = item.get('page')
                last_unit['budget_page_stop'] = toc_data[item_id+1].get('page')
    if last_unit:
        last_ministry['budgetary_units'].append(last_unit)
    
    ministries_toc['จังหวัดและกลุ่มจังหวัด'] = last_ministry

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
            convert_province_data_to_toc(toc_data, ministries_toc, filename)
        else:
            convert_toc_data_to_toc(toc_data, ministries_toc, filename)
         
    # Split data to ministry level
    for ministry, toc in ministries_toc.items():
        if re.search(r"^แผนงาน", ministry): # skip แผนงาน
            continue
        with open(os.path.join(output_path, f"{ministry}.json"), "w") as f:
            json.dump(toc, f, indent=4, ensure_ascii=False)
                    