from typing import List, Dict, Tuple, Any
import numpy as np
import cv2
import re
import numpy.typing as npt
from .budget_tree_page_detector import get_white_column_ranges
from .ocr_engine import extract_texts_from_page, detect_text_lines, read_texts
from .budget_text_manager import split_pair_budget_amount

def read_budget_tree_in_page(
    page: npt.NDArray,
    top_margin_percentage: float=0.05,
) -> List[Dict[str, Any]]:

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
    
    budget_items_texts = extract_texts_from_page(text_side)
    budget_amounts_texts = extract_texts_from_page(budget_side)
    
    # Split and pair data into dict objects
    budget_tree_data = split_pair_budget_amount(budget_items_texts, budget_amounts_texts)
    
    return budget_tree_data

def detect_separator_lines(page: npt.NDArray) -> List[Tuple[int, int, int, int]]:
    # Convert to grayscale if necessary
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY) if len(page.shape) == 3 else page

    # Binarize the image (invert so text/lines are white, background is black)
    _, binarized = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Define a horizontal kernel that is 60% of the page width
    min_width = int(gray.shape[1] * 0.6)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_width, 1))

    # Isolate horizontal lines using morphological opening
    lines_mask = cv2.morphologyEx(binarized, cv2.MORPH_OPEN, kernel)

    # Find contours of the detected lines
    contours, _ = cv2.findContours(lines_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bboxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w >= min_width:
            bboxes.append((x, y, x + w, y + h))

    return bboxes

def read_core_content_in_page(
    page: npt.NDArray,
    top_margin_percentage: float=0.05,
) -> Dict[str, str]:
    
    # Detect separator lines    
    separator_bboxes = detect_separator_lines(page)
    if not separator_bboxes: # detect no lines
        return {}
    
    # Get the lowest line and crop page again
    separator_bboxes = sorted(
        separator_bboxes, 
        key=lambda bb: bb[3] # y2
    )
    # Check if there are more than 3 lines
    if len(separator_bboxes) > 3:
        lowest_line = separator_bboxes[2]
        highest_table = separator_bboxes[3]
        # Crop page
        top_margin = int(page.shape[0] * top_margin_percentage)
        cropped_page = page[lowest_line[3]+top_margin:highest_table[1], :]
    else:
        lowest_line = separator_bboxes[-1]
        # Crop page
        top_margin = int(page.shape[0] * top_margin_percentage)
        cropped_page = page[lowest_line[3]+top_margin:, :]
    
    
    # Detect bbox
    text_lines = detect_text_lines(cropped_page)
    if not text_lines:
        return {}
    
    # Separate bbox to title and content
    all_x1 = [
        l[1][0] for l in text_lines
    ]
    x_split_point = ((max(all_x1) - min(all_x1)) / 2) + min(all_x1)
    contents = []
    current_group = []
    for text_line in text_lines:
        _, bbox = text_line
        if bbox[0] < x_split_point: # x1 < split line
            if current_group:
                contents.append(current_group)
            current_group = []
            continue
        current_group.append(text_line)
    if current_group:
        contents.append(current_group)
        
    result_data = {}
    for topic, text_lines in zip(['vision', 'mission'], contents):
        result_data[topic] = read_texts([
            l[0] for l in text_lines
        ])
            
    return result_data

def read_budget_plan_in_page(page: npt.NDArray,
    top_margin_percentage: float=0.05,
    bottom_margin_percentage: float=0.2,
) -> Dict[str, str]:
    
    # Crop page
    top_margin = int(page.shape[0] * top_margin_percentage)
    bottom_margin = int(page.shape[0] * bottom_margin_percentage)
    cropped_page = page[top_margin:bottom_margin, :]
    
    extracted_text = extract_texts_from_page(cropped_page)
    
    result = {}
    # Search for budget plan header
    budget_plan_matched = re.search(r"(7\.\d)\s(.+?)(?=$|\n)", extracted_text)
    if budget_plan_matched:
        result['budget_plan_prefix'] = budget_plan_matched.group(1)
        result['budget_plan_name'] = budget_plan_matched.group(2)
    else: # search for only `แผนงาน`
        budget_plan_name_matched = re.search(r"แผนงาน.+?(?=$|\n)", extracted_text)
        if budget_plan_name_matched:
            result['budget_plan_name'] = budget_plan_name_matched.group(0)
    
    # If no budget plan; search for output header instead
    if result.get('budget_plan_prefix') is None:   
        output_prefix_matched = re.search(r"(7\.\d)\.\d", extracted_text)
        if output_prefix_matched:
            result['budget_plan_prefix'] = output_prefix_matched.group(1)
    # Search for output name
    output_name_matched = re.search(r"(7\.\d)\.\d\s(.+)(?=$|\n)", extracted_text)
    if output_name_matched:
        output_name = output_name_matched.group(2)
        # Add type
        output_type = 'OUTPUT'
        if re.search(r"โครงการ", output_name):
            output_type = 'PROJECT'
        result['output_type'] = output_type
        # Clean name
        if ":" in output_name:
            output_name = re.sub(".+?:", "", output_name).strip()
        result['output_name'] = output_name
    
    return result