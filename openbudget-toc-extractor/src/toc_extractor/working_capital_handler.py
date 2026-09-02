from typing import List, Dict, Any
import re
from .unit_name_manager import UnitNameManager

def convert_w_capital_data_to_toc(
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
                if re.search(r"นิติ", title):
                    continue
                # is ministry
                if last_ministry:
                    # Check and add last unit
                    if last_unit:
                        last_ministry['budgetary_units'].append(last_unit)
                    ministry_name = last_ministry.get('name', '').strip()
                    if ministry_name in ministries_toc:
                        ministries_toc[ministry_name]['budgetary_units'].extend(last_ministry['budgetary_units'])
                        continue
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
                    title,
                    ministries=['ทุนหมุนเวียน', 'กองทุนและเงินทุนหมุนเวียน']
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
            
    if last_unit and last_ministry:
        last_ministry['budgetary_units'].append(last_unit)
        ministries_toc[last_ministry.get('name', '').strip()] = last_ministry
