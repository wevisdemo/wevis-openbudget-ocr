from typing import List, Dict, Any
import numpy.typing as npt
import pandas as pd
import numpy as np
from tqdm import tqdm
from .text_ocr import read_budget_data_in_page, read_core_content_in_page, read_budget_plan_in_page
from .tree_manager import construct_tree_data, transform_budget_plan_data, rearrange_budget_plan_chunks, tree_df_to_nested_dict
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
        document: str,
        ministry_budget_page: Page
    ):
        self.ministry_name = ministry_name
        self.ministry_budget_page = ministry_budget_page
        self.budgetary_units: List[UnitBudget] = []
        
        self.document = document
        
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
            'document': self.document,
            'page': self.ministry_budget_page.page_num,
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
        
        ministry_header_df = pd.DataFrame(
            [{
                'budget_type': 'MINISTRY',
                'name_1': self.ministry_name,
                'amount': budgetary_unit_tree_df[
                    budgetary_unit_tree_df['name_2'] != ''
                ]['amount'].sum()
            }],
            columns=BUDGET_TREE_DEFAULT_COLUMNS
        ).fillna('')
        
        return pd.concat(
            [ministry_header_df, budgetary_unit_tree_df],
            ignore_index=True
        )
        
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
            'vision': self.get_vision(),
            'mission': self.get_mission(),
            'document': self.document,
            'page': self.unit_budget_page.page_num,
            'budget_plans': budget_plans
        }

    def get_budget_tree(self) -> pd.DataFrame:
        
        # Extract all output tree
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
        
        # # Combine output with same budget plan
        # budget_plans_tree_df = rearrange_budget_plan_chunks(output_tree_df)
        
        # # TODO: read amount from page instead of using sum
        # unit_header_df = pd.DataFrame(
        #     [{
        #         'budget_type': 'BUDGETARY_UNIT',
        #         'name_2': self.unit_name,
        #         'amount': output_tree_df[
        #             output_tree_df['name_3'] != ''
        #         ]['amount'].sum()
        #     }],
        #     columns=BUDGET_TREE_DEFAULT_COLUMNS
        # ).fillna('')
        
        # # Add document
        # budget_unit_df = pd.concat(
        #     [unit_header_df, budget_plans_tree_df],
        #     ignore_index=True
        # )
        # budget_unit_df.loc[:, 'document'] = self.document
        
        return pd.DataFrame(columns=BUDGET_TREE_DEFAULT_COLUMNS)
        
        
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
        
        # Budget tree
        self.budget_tree = None
        
    def read_budget_plan_data(self) -> None:
        budget_detail_page = self.output_pages[0]
        bueget_plan = read_budget_plan_in_page(budget_detail_page.page)
        
        self.budget_plan_prefix = bueget_plan.get('budget_plan_prefix')
        self.budget_plan_name = bueget_plan.get('budget_plan_name')
        self.output_name = bueget_plan.get('output_name')
        self.output_type = bueget_plan.get('output_type')
        
    def to_dict(self) -> Dict[str, Any]:
        # Read Budget Plan/Output details
        self.read_budget_plan_data()
        
        output_dict = {
            'budget_plan_prefix': self.budget_plan_prefix,
            'budget_plan_name': self.budget_plan_name,
            'name': self.output_name,
            'type': self.output_type,
            'document': None,
            'page': self.output_pages[0].page_num,
        }
        
        # Read tree
        if self.budget_tree is None:
            _ = self.get_budget_tree()
            
        output_dict['budget_details'] = self.budget_tree
        
        return output_dict
       
    def get_budget_tree(self) -> pd.DataFrame:
        if self.budget_tree is None:
            self.read_budget_tree(self.output_pages[1:])
            
        # TODO: construct buduget tree df
        return pd.DataFrame(columns=BUDGET_TREE_DEFAULT_COLUMNS)
    
    def read_budget_tree(self, pages: List[Page]) -> None:
        
        for page in tqdm(
            pages, 
            leave=False,
            desc="process output", unit="pages",
            position=2
        ):
            # Read budget data
            budget_data = read_budget_data_in_page(page.page)
            budget_data = [
                item for item in budget_data if item.get('name', None) is not None
            ]
            # Add page
            for item in budget_data:
                item['page'] = page.page_num
            
            # Convert to tree dict
            budget_tree = construct_tree_data(budget_data)
            self.budget_tree = budget_tree
