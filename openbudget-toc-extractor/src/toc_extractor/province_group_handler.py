from typing import List, Dict, Any
import re

def province_group_data_to_toc(
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
