from typing import List, Dict, Any
import numpy as np
import numpy.typing as npt
from .budget_tree_page_detector import get_white_column_ranges
from .ocr_engine import extract_texts
from .budget_text_manager import split_pair_budget_amount

def read_budget_tree_in_page(
    page: npt.ArrayLike,
    top_margin_percentage: float=0.05,
) -> List[Dict[str, Any]]:
    page = np.asarray(page)
    # Split the page into 2 parts
    white_spaces = get_white_column_ranges(page)
    biggest_white_space = sorted(
        white_spaces, 
        key=lambda xbox: xbox[1] - xbox[0], 
        reverse=True
    )[0]
    # Get center of the space
    split_point = biggest_white_space[0] + ((biggest_white_space[1] - biggest_white_space[0]) / 2)
    split_point = int(split_point)
    
    # Crop page
    top_margin = int(page.shape[0] * top_margin_percentage)
    text_side = page[top_margin:, :split_point]
    budget_side = page[top_margin:, split_point:]
    
    budget_items_texts = extract_texts(text_side)
    budget_amounts_texts = extract_texts(budget_side)
    
    # Split and pair data into dict objects
    budget_tree_data = split_pair_budget_amount(budget_items_texts, budget_amounts_texts)
    
    return budget_tree_data