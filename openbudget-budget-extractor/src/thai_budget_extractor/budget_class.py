from typing import List, Dict, Any
import numpy.typing as npt
import pandas as pd
import numpy as np
from tqdm import tqdm
from .text_ocr import (
    read_budget_data_in_page, 
    read_core_content_in_page, 
    read_budget_plan_in_page, 
    read_budget_amount_in_unit_page,
    read_budget_amount_in_output_page,
    read_lgo_full_name,
    read_budget_amount_in_lgo_page
)
from .tree_manager import construct_tree_data, transform_budget_plan_data, convert_budget_dict_to_df

class Page():
    def __init__(
        self,
        page: npt.NDArray,
        page_num: int
    ):
        self.page = page
        self.page_num = page_num
        
class MinistryBudget():
    def __init__(
        self,
        ministry_name: str,
        document: str,
        ministry_budget_page: Page,
        budget_pages: List[Page]|None=None,
    ):
        self.ministry_name = ministry_name
        self.ministry_budget_page = ministry_budget_page
        self.budgetary_units: List[UnitBudget] = []
        
        self.budget_pages = budget_pages
        
        self.document = document
        
        self.vision = None
        self.mission = None
        
        self.amount = None
        
        self.budget_tree = None
        
    def get_vision(self) -> str|None:
        if self.vision is None:
            self.read_budget_data()
        return self.vision
        
    def get_mission(self) -> str|None:
        if self.mission is None:
            self.read_budget_data()
        return self.mission
    
    def get_budget_amount(self) -> int|None:
        if self.amount is None:
            self.read_budget_data()
        return self.amount
    
    def read_budget_data(self) -> None:
        core_content = read_core_content_in_page(self.ministry_budget_page.page)
        self.vision = core_content.get('vision', None)
        self.mission = core_content.get('mission', None)
        budget_amount = read_budget_amount_in_unit_page(self.ministry_budget_page.page)
        self.amount = budget_amount
        
    def to_dict(self) -> Dict[str, Any]:
        
        if self.budget_tree:
            return self.budget_tree
        
        ministry_dict = {
            'name': self.ministry_name,
            'type': 'MINISTRY',
            'vision': self.get_vision(),
            'mission': self.get_mission(),
            'amount': self.get_budget_amount(),
            'document': self.document,
            'page': self.ministry_budget_page.page_num
        }
        
        if self.budget_pages is not None:
            budget_plan = read_budget_plan_in_page(self.budget_pages[0].page)
            budget_amount = read_budget_amount_in_output_page(self.budget_pages[0].page)
            budgetary_units_tree = {
                "prefix": budget_plan.get('budget_plan_prefix'),
                "name": budget_plan.get('budget_plan_name'),
                "type": "BUDGET_PLAN",
                "amount": budget_amount,
                "page": self.budget_pages[0].page_num,
            }
            for _ in tqdm(range(1), desc=self.ministry_name, position=0):
                for _ in tqdm(range(1), desc=self.ministry_name, position=1):
                    budgetary_units_tree['outputs'] = read_budget_tree(self.budget_pages[1:])
        else:
            budgetary_units_tree = [
                budget_unit.to_dict() for budget_unit in tqdm(
                    self.budgetary_units, 
                    desc=self.ministry_name,
                    position=0
                )
            ]
        ministry_dict['budgetary_units'] = budgetary_units_tree
        
        self.budget_tree = ministry_dict
        return self.budget_tree
        
    def get_budget_tree_df(self) -> pd.DataFrame:
        
        budget_tree_df = convert_budget_dict_to_df(self.to_dict())
        return budget_tree_df
    
class CentralBudget(MinistryBudget):
    
    def to_dict(self) -> Dict[str, Any]:
            
        ministry_dict = {
            'name': self.ministry_name,
            'type': 'MINISTRY',
            'vision': self.get_vision(),
            'mission': self.get_mission(),
            'amount': self.get_budget_amount(),
            'document': self.document,
            'page': self.ministry_budget_page.page_num
        }
        
        if self.budget_pages is not None:
            for _ in tqdm(range(1), desc=self.ministry_name, position=0):
                for _ in tqdm(range(1), desc=self.ministry_name, position=1):
                    budgetary_units_tree = read_budget_tree(self.budget_pages[1:])
        else:
            budgetary_units_tree = [
                budget_unit.to_dict() for budget_unit in tqdm(
                    self.budgetary_units, 
                    desc=self.ministry_name,
                    position=0
                )
            ]
            
        ministry_dict['budgetary_units'] = budgetary_units_tree
        return ministry_dict
        
class UnitBudget():
    
    def __init__(
        self,
        unit_name: str,
        document: str,
        unit_budget_page: Page
    ):
        self.unit_name = unit_name
        self.unit_budget_page = unit_budget_page
        self.outputs: List[OutputBudget] = []
        
        self.document = document
        
        self.vision = None
        self.mission = None
        
        self.amount = None
        
    def get_vision(self) -> str|None:
        if self.vision is None:
            self.read_budget_data()
        return self.vision
            
    def get_mission(self) -> str|None:
        if self.mission is None:
            self.read_budget_data()
        return self.mission
    
    def get_budget_amount(self) -> int|None:
        if self.amount is None:
            self.read_budget_data()
        return self.amount
    
    def read_budget_data(self) -> None:
        core_content = read_core_content_in_page(self.unit_budget_page.page)
        self.vision = core_content.get('vision', None)
        self.mission = core_content.get('mission', None)
        budget_amount = read_budget_amount_in_unit_page(self.unit_budget_page.page)
        self.amount = budget_amount
        
    def to_dict(self) -> Dict[str, Any]:
        
        outputs = [
            output.to_dict() for output in tqdm(
                self.outputs, 
                desc=self.unit_name,
                position=1,
                leave=False
            )
        ]
        
        # Add each output within budget plan
        budget_plans = transform_budget_plan_data(outputs)
                
        return {
            'name': self.unit_name,
            'type': 'BUDGETARY_UNIT',
            'vision': self.get_vision(),
            'mission': self.get_mission(),
            'amount': self.get_budget_amount(),
            'document': self.document,
            'page': self.unit_budget_page.page_num,
            'budget_plans': budget_plans
        }
        
class LocalOrgBudget(UnitBudget):
    
    def read_budget_data(self) -> None:
        full_name = read_lgo_full_name(self.unit_budget_page.page)
        if full_name:
            # TODO: normalize name with lgo_data.csv
            self.unit_name = full_name
        self.vision = ""
        self.mission = ""
        budget_amount = read_budget_amount_in_lgo_page(self.unit_budget_page.page)
        self.amount = budget_amount
        
    def to_dict(self) -> Dict[str, Any]:
            
        # TODO: read budget tree in unit page
        outputs = []
        
        # Add each output within budget plan
        budget_plans = transform_budget_plan_data(outputs)
                
        return {
            'name': self.unit_name,
            'type': 'BUDGETARY_UNIT',
            'vision': self.get_vision(),
            'mission': self.get_mission(),
            'amount': self.get_budget_amount(),
            'document': self.document,
            'page': self.unit_budget_page.page_num,
            'budget_plans': budget_plans
        }
    
class OutputBudget():
    def __init__(
        self,
        output_pages: List[Page]
    ):
        self.output_pages = output_pages
        self.output_name = None
        self.output_type = None
        
        # Budget plan
        self.budget_plan_prefix = None
        self.budget_plan_name = None
        self.budget_plan_amount = None
        
        # Budget tree
        self.budget_tree = None
        
    def read_budget_plan_data(self) -> None:
        budget_detail_page = self.output_pages[0]
        bueget_plan = read_budget_plan_in_page(budget_detail_page.page)
        
        self.budget_plan_prefix = bueget_plan.get('budget_plan_prefix')
        self.budget_plan_name = bueget_plan.get('budget_plan_name')
        self.output_name = bueget_plan.get('output_name')
        self.output_type = bueget_plan.get('output_type')
        
        budget_amount = read_budget_amount_in_output_page(budget_detail_page.page)
        self.budget_plan_amount = budget_amount
        
    def to_dict(self) -> Dict[str, Any]:
        # Read Budget Plan/Output details
        self.read_budget_plan_data()
        
        output_dict = {
            'budget_plan_prefix': self.budget_plan_prefix,
            'budget_plan_name': self.budget_plan_name,
            'budget_plan_amount': self.budget_plan_amount,
            'name': self.output_name,
            'type': self.output_type,
            'page': self.output_pages[0].page_num,
        }
        
        # Read tree
        if self.budget_tree is None:
            budget_tree = read_budget_tree(self.output_pages[1:])
            self.budget_tree = budget_tree
            
        output_dict['outputs'] = self.budget_tree          
        
        return output_dict

def read_budget_tree(pages: List[Page]) -> List[Dict[str, Any]]:
        
    budget_data = []
    for page in tqdm(
        pages, 
        leave=False,
        desc="process output", unit="pages",
        position=2
    ):
        # Read budget data
        _current_page_budget_data = read_budget_data_in_page(page.page)
        _current_page_budget_data = [
            item for item in _current_page_budget_data if item.get('name', None) is not None
        ]
        # Add page
        for item in _current_page_budget_data:
            item['page'] = page.page_num
        budget_data.extend(_current_page_budget_data)
        
    # Convert to tree dict
    budget_tree = construct_tree_data(budget_data)
    return budget_tree
