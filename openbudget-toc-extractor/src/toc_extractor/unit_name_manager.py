from typing import List
import re
import pandas as pd
from thefuzz import process

def get_closest_match(
    target_string: str, 
    string_list: List[str], 
    threshold: int=95
) -> str|None:
    """
    Finds the closest string from a list based on a similarity threshold.
    
    :param target_string: The string to search for.
    :param string_list: A list of strings to compare against.
    :param threshold: The minimum score (0-100) required to return a match.
    :return: The closest string or None if no match meets the threshold.
    """
    if not string_list:
        return None

    # extractOne returns a tuple: (best_match_string, score)
    result = process.extractOne(target_string, string_list)
    
    if result:
        best_match, score = result # type: ignore
        if score >= threshold:
            return best_match
            
    return None

MIN_AGC_PATH = "data/min_agc_names.csv"

class UnitNameManager():
    
    _unit_name_df = None
    
    @classmethod
    def get_ministry_name(cls, original_name: str) -> str:
        if cls._unit_name_df is None:
            cls._unit_name_df = pd.read_csv(MIN_AGC_PATH)
            
        all_ministries_name = list(cls._unit_name_df['min_name'].unique())
        matched_name = get_closest_match(
            original_name,
            all_ministries_name
        )
        if matched_name:
            return matched_name
        return original_name

    @classmethod
    def get_unit_name(cls, original_name: str, ministries:List[str]=[]) -> str:
        if cls._unit_name_df is None:
            cls._unit_name_df = pd.read_csv(MIN_AGC_PATH)
        
        df = cls._unit_name_df
        if ministries:
            df = df[df['min_name'].isin(ministries)]
        all_units_name = list(df['agc_name'].unique())
        matched_name = get_closest_match(
            original_name,
            all_units_name
        )
        
        result_name = original_name
        if matched_name:
            result_name = matched_name
        
        # Clean กองทุน
        if re.search(r"เพื่อกองทุน", result_name):
            result_name = re.sub(r".+?เพื่อ(?=กองทุน)", "", result_name).strip()
        elif re.search(r"สำหรับ\s?กองทุน", result_name):
            result_name = re.sub(r".+?สำหรับ\s?(?=กองทุน)", "", result_name).strip()
        
        return result_name
    