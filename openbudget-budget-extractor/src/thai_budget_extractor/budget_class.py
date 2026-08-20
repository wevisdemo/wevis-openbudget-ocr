from typing import List, Dict, Any
import numpy.typing as npt
import pandas as pd
from tqdm import tqdm
from .text_ocr import read_budget_tree_in_page, read_core_content_in_page
from .tree_manager import construct_tree_df
from .constants import BUDGET_TREE_DEFAULT_COLUMNS

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
        ministry_budget_page: Page
    ):
        self.ministry_name = ministry_name
        self.ministry_budget_page = ministry_budget_page
        self.budgetary_units: List[UnitBudget] = []
        
        self.vision = None
        self.mission = None
        
    def get_vision(self) -> str|None:
        if self.vision is None:
            self.read_budget_data()
        return self.vision
        
    def get_mission(self) -> str|None:
        if self.mission is None:
            self.read_budget_data()
        return self.mission
    
    def read_budget_data(self) -> None:
        core_content = read_core_content_in_page(self.ministry_budget_page.page)
        self.vision = core_content.get('vision', None)
        self.mission = core_content.get('mission', None)
        
    def to_dict(self) -> Dict[str, Any]:
        
        ministry_dict = {
            'name': self.ministry_name,
            'vision': self.get_vision(),
            'mission': self.get_mission(),
            'budgetray_units': [
                budget_unit.to_dict() for budget_unit in tqdm(
                    self.budgetary_units, 
                    desc=self.ministry_name,
                    position=0
                )
            ]
        }
        
        return ministry_dict
        
    def get_budget_tree(self) -> pd.DataFrame:
        
        # TODO: OCR page to get budget amount and attach to the top of tree
        budgetary_unit_tree_df = pd.concat(
            [
                budget_unit.get_budget_tree() for budget_unit in tqdm(
                    self.budgetary_units, 
                    desc=self.ministry_name,
                    position=0
                )
                
            ],
            ignore_index=True
        )
        
        return budgetary_unit_tree_df
        
class UnitBudget():
    
    def __init__(
        self,
        unit_name: str,
        unit_budget_page: Page
    ):
        self.unit_name = unit_name
        self.unit_budget_page = unit_budget_page
        self.outputs: List[OutputBudget] = []
        
        self.vision = None
        self.mission = None
        
    def get_vision(self) -> str|None:
        if self.vision is None:
            self.read_budget_data()
        return self.vision
            
    def get_mission(self) -> str|None:
        if self.mission is None:
            self.read_budget_data()
        return self.mission
    
    def read_budget_data(self) -> None:
        core_content = read_core_content_in_page(self.unit_budget_page.page)
        self.vision = core_content.get('vision', None)
        self.mission = core_content.get('mission', None)
        
    def to_dict(self) -> Dict[str, Any]:
            
        budgetary_unit_dict = {
            'name': self.unit_name,
            'vision': self.get_vision(),
            'mission': self.get_mission(),
            'budget_plans': []
        }
        
        return budgetary_unit_dict

    def get_budget_tree(self) -> pd.DataFrame:
        # TODO: OCR page to get budget amount and attach to the top of tree
        output_tree_df = pd.concat(
            [
                output.get_budget_tree() for output in tqdm(
                    self.outputs, 
                    leave=False,
                    desc=self.unit_name,
                    position=1
                )
            ],
            ignore_index=True
        )
        
        return output_tree_df
        
        
class OutputBudget():
    def __init__(
        self,
        output_pages: List[Page]
    ):
        self.output_pages = output_pages
        self.output_name = None
        
    def to_dict(self) -> Dict[str, Any]:
                
        output_dict = {
            'name': self.output_name
        }
        
        return output_dict
        
       
    def get_budget_tree(self) -> pd.DataFrame:
        # TODO: ocr pages & construct budget tree
        budget_detail_page = self.output_pages[0]
        budget_tree_pages = self.output_pages[1:]
        budget_tree = self.read_budget_tree(budget_tree_pages)
        return budget_tree
    
    def read_budget_tree(self, pages: List[Page]) -> pd.DataFrame:
        
        tree_df = pd.DataFrame(columns=BUDGET_TREE_DEFAULT_COLUMNS)
        for page in tqdm(
            pages, 
            leave=False,
            desc="process output", unit="pages",
            position=2
        ):
            budget_tree_data = read_budget_tree_in_page(page.page)
            new_df = construct_tree_df(budget_tree_data, base_depth=4)
            # Add page number
            new_df['page'] = page.page_num
            tree_df = pd.concat(
                [tree_df, new_df],
                ignore_index=True
            )
            
        return tree_df
