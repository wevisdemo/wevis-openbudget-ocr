from typing import List, Dict, Tuple, Any
from functools import cache
import re
import pandas as pd
from .utilities import clean_lgo_name
from rapidfuzz import fuzz

         
class LGONameMatcher:
    lgo_name_df = None
    
    @classmethod
    def get_full_name(cls, province: str | None, name: str) -> str:
        if cls.lgo_name_df is None:
            cls.lgo_name_df = load_thailand_province_data()
            
        exact_matched = cls.lgo_name_df[cls.lgo_name_df['ชื่อ อปท'] == name]
        if len(exact_matched) == 1:
            row = exact_matched.iloc[0]
            return f"{row['ชื่อ อปท']} {row['อำเภอ']} {row['จังหวัด']}"
            
        df = cls.lgo_name_df.copy()
        df['score'] = df['ชื่อ อปท'].apply(lambda x: fuzz.ratio(name, str(x)))
        matched = df[df['score'] > 90]
        
        if matched.empty:
            print("empty", name, province)
            return ""
            
        if len(matched) == 1:
            row = matched.iloc[0]
            return f"{row['ชื่อ อปท']} {row['อำเภอ']} {row['จังหวัด']}"
            
        if province:
            prov_matched = matched[matched['จังหวัด'] == province]
            if not prov_matched.empty:
                matched = prov_matched
        
        best_match = matched.loc[matched['score'].idxmax()]
        return f"{best_match['ชื่อ อปท']} {best_match['อำเภอ']} {best_match['จังหวัด']}"
        
THAILAND_LGO_PATH = "example/lgo_data.csv"
def load_thailand_province_data() -> pd.DataFrame:

    # Load csv
    lgo_df = pd.read_csv(THAILAND_LGO_PATH)
    lgo_df.loc[:, 'ชื่อ อปท'] = lgo_df['ประเภท'] + lgo_df['ชื่อ']
    lgo_df.loc[:, 'อำเภอ'] = lgo_df['อำเภอ'].apply(
        lambda name: 'อำเภอ' + str(name).strip()
    )
    lgo_df.loc[:, 'จังหวัด'] = lgo_df['จังหวัด'].apply(
        lambda name: 'จังหวัด' + str(name).strip()
    )
    
    result = lgo_df.groupby('จังหวัด').apply(
        lambda x: dict(zip(x['ชื่อ อปท'], x['อำเภอ']))
    ).to_dict()
    
    return lgo_df
    
def lgo_data_to_toc(
    toc_data: List[Dict[str, Any]],
    ministries_toc: Dict[str, Any], 
    filename: str
):
    toc_level = None
    last_unit = None
    last_province = ''
    
    THAILAND_LGO_DATA = load_thailand_province_data()
    
    last_ministry = ministries_toc.get('องค์กรปกครองส่วนท้องถิ่น', None)
    if last_ministry is None:
        last_ministry = {
            'name': 'องค์กรปกครองส่วนท้องถิ่น',
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
        elif item.get('level') == toc_level + 2: # unit group
            unit_name = item.get('title', '0')
            # Check for province group
            if re.search(r"ใน.*จังหวัด", unit_name):
                last_province = re.search(r"จังหวัด.*", unit_name).group(0) # type: ignore
        elif item.get('level') >= toc_level + 3: # unit
            unit_name = item.get('title', '0')
            if re.search(r"ใน.*จังหวัด", unit_name):
                last_province = re.search(r"จังหวัด.*", unit_name).group(0) # type: ignore
                continue
            if last_unit and re.search(r"^\d", unit_name):
                last_unit['budget_page_start'] = item.get('page')
                last_unit['budget_page_stop'] = toc_data[item_id+1].get('page')
                continue
            
            last_ministry['budgetary_units'].append(last_unit)
            
            # Process unit name
            cleaned_unit_name = clean_lgo_name(unit_name)
            if re.search(r"เทศบาล|ตำบล", cleaned_unit_name) and THAILAND_LGO_DATA is not None:
                # Add อำเภอ
                unit_full_name = LGONameMatcher.get_full_name(
                    province=last_province, 
                    name=cleaned_unit_name
                )
                cleaned_unit_name = unit_full_name
                
            last_unit = {
                'name': cleaned_unit_name.strip(),
                'document': filename,
                'unit_page': item.get('page'),
            }
    if last_unit:
        last_ministry['budgetary_units'].append(last_unit)
        
    ministries_toc['องค์กรปกครองส่วนท้องถิ่น'] = last_ministry
