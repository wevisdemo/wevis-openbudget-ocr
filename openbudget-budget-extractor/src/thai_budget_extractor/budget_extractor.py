from typing import List, Dict, Any
import pymupdf
import cv2
import numpy as np
import numpy.typing as npt
from .constants import MINISTRY_NAMES
from .budget_class import MinistryBudget, UnitBudget, OutputBudget, Page
from .budget_tree_page_detector import is_budget_tree_page

def extract_budget_object(
    pdf_path: str,
    toc_data: List[Dict[str, Any]],
) -> List[MinistryBudget]:
    # Load document
    doc = pymupdf.open(pdf_path)
    def get_page_np_array(page_num: int) -> npt.NDArray:
        page_index = page_num - 1
        pix = doc[page_index].get_pixmap(colorspace=pymupdf.csGRAY, alpha=False, dpi=300)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        # Adaptive thresholding handles shadows/gradients much better
        binary_img = cv2.adaptiveThreshold(
            img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        return binary_img
    
    # Initialize budget object
    ministries = []
    ministry = None
    for toc_obj in toc_data:
        title = toc_obj.get('unit_title', '')
        if title in MINISTRY_NAMES:
            if ministry is not None:
                ministries.append(ministry)
            # Load page into np.array
            ministry_page_num = toc_obj.get('unit_page', 0)
            ministry_budget_page = get_page_np_array(ministry_page_num)
            ministry = MinistryBudget(
                ministry_name=title,
                ministry_budget_page=Page(ministry_budget_page, ministry_page_num)
            )
            continue
        
        if ministry is None:
            continue
        
        unit_budget_page_num = toc_obj.get('unit_page', 0)
        unit_budget_page = get_page_np_array(unit_budget_page_num)
        budgetary_unit = UnitBudget(
            unit_name=title,
            unit_budget_page=Page(
                unit_budget_page,
                unit_budget_page_num
            )
        )
        
        # Separate & Group each output/project in budget pages
        budget_start_page = toc_obj.get('budget_page_start', 0)
        budget_stop_page = toc_obj.get('budget_page_stop', -1)
        
        budget_pages = [
            Page(get_page_np_array(_page_num), _page_num)
            for _page_num in range(budget_start_page, budget_stop_page)
        ]
        mask = [is_budget_tree_page(page.page) for page in budget_pages]
        
        output_groups = []
        curr_group = []
        for i, is_tree in enumerate(mask):
            if i == 0: # first page
                curr_group = [budget_pages[i]]
                continue
            if not is_tree and mask[i-1]: # first page after tree
                output_groups.append(curr_group)
                # Set up new group
                curr_group = [budget_pages[i]]
                continue
            elif is_tree:
                curr_group.append(budget_pages[i])
        if curr_group:
            output_groups.append(curr_group) # add last group
            
        budgetary_unit.outputs = [
            OutputBudget(pages) for pages in output_groups
        ]
        ministry.budgetary_units.append(budgetary_unit)
    
    # Add the last ministry
    if ministry is not None and ministry not in ministries:
        ministries.append(ministry)
        
    return ministries
    