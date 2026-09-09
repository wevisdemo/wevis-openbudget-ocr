from typing import List, Dict, Any
import pymupdf
import os
import cv2
import numpy as np
import numpy.typing as npt
from .constants import MINISTRY_NAMES
from .budget_class import MinistryBudget, UnitBudget, OutputBudget, Page, CentralBudget, LocalOrgBudget
from .budget_tree_page_detector import is_budget_tree_page


class PdfDoc():
    _doc = None
    _path = None
    
    @classmethod
    def load_doc(cls, pdf_path):
        if pdf_path == cls._path and cls._doc is not None:
            return cls._doc
        else:
            cls._doc = pymupdf.open(pdf_path)
            cls._path = pdf_path
        return cls._doc

def load_pdf_page(pdf_path: str, page_num: int):
    doc = PdfDoc.load_doc(pdf_path)
    page_index = page_num - 1
    pix = doc[page_index].get_pixmap(colorspace=pymupdf.csGRAY, alpha=False, dpi=300)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    # Adaptive thresholding handles shadows/gradients much better
    binary_img = cv2.adaptiveThreshold(
        img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    return binary_img
    
def extract_budget_object(toc_data: Dict[str, Any], pdf_dir:str='pdf') -> MinistryBudget:
    
    budgetary_units = []
    for toc_budgetary_unit in toc_data.get('budgetary_units', []):
        
        # Load page
        unit_doc_path = toc_budgetary_unit.get('document')
        unit_page_num = toc_budgetary_unit.get('unit_page')
        page_img = load_pdf_page(
            os.path.join(pdf_dir, unit_doc_path),
            unit_page_num
        )
        
        # Instantiate UnitBudget
        budgetary_unit = UnitBudget(
            unit_name=toc_budgetary_unit.get('name'),
            document=unit_doc_path,
            unit_budget_page=Page(
                page_img,
                unit_page_num
            )
        )
        
        # Instantiate Outputs
        budget_start_page = toc_budgetary_unit.get('budget_page_start', 0)
        budget_stop_page = toc_budgetary_unit.get('budget_page_stop', -1)
        
        if budget_start_page is None or budget_stop_page is None or budget_stop_page < budget_start_page:
            unit_name = toc_budgetary_unit.get('name', '')
            import re
            if re.search(r"^(เทศบาล|องค์การ)", unit_name):
                budgetary_unit = LocalOrgBudget(
                    unit_name=toc_budgetary_unit.get('name'),
                    document=unit_doc_path,
                    unit_budget_page=Page(
                        page_img,
                        unit_page_num
                    )
                )
                budgetary_units.append(budgetary_unit)
                continue
            budget_pages = []
        else:
            budget_pages = [
                Page(load_pdf_page(os.path.join(pdf_dir, unit_doc_path), _page_num), _page_num)
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
        budgetary_units.append(budgetary_unit)
        
    ministry_doc = toc_data.get('document', '')
    ministry_budget_pages = None
    if toc_data.get('budget_page_start'):
        budget_page_start = toc_data.get('budget_page_start', 0)
        budget_page_stop = toc_data.get('budget_page_stop', 1)
        # Filter only the first budget page and the rest of budget tree
        ministry_budget_pages = [Page(
            load_pdf_page(os.path.join(pdf_dir ,ministry_doc), budget_page_start), 
            budget_page_start
        )]
        ministry_budget_pages.extend([
            Page(
                load_pdf_page(os.path.join(pdf_dir ,ministry_doc), p_num),
                p_num
            ) for p_num in range(budget_page_start, budget_page_stop) if is_budget_tree_page(load_pdf_page(os.path.join(pdf_dir ,ministry_doc), p_num))
        ])
        
    ministry_name = toc_data.get('name', '')
    if ministry_name == 'งบกลาง':
        ministry = CentralBudget(
            toc_data.get('name', ''),
            ministry_doc,
            Page(
                load_pdf_page(os.path.join(pdf_dir ,ministry_doc), toc_data.get('unit_page', 0)), 
                toc_data.get('unit_page', 0)
            ),
            budget_pages=ministry_budget_pages
        )
    else:
        ministry = MinistryBudget(
            toc_data.get('name', ''),
            ministry_doc,
            Page(
                load_pdf_page(os.path.join(pdf_dir ,ministry_doc), toc_data.get('unit_page', 0)), 
                toc_data.get('unit_page', 0)
            ),
            budget_pages=ministry_budget_pages
        )
    ministry.budgetary_units = budgetary_units
    
    return ministry
