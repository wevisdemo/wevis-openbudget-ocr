from typing import List, Dict, Tuple, Any
import numpy as np
import cv2
import re
from rapidfuzz import fuzz
import numpy.typing as npt
from .budget_tree_page_detector import get_white_column_ranges
from .ocr_engine import extract_texts_from_page, detect_text_lines, detect_amount_text_lines, read_texts
from .budget_text_manager import group_aligned_bboxes, get_prefix_pattern, clean_text_prefix


def read_budget_data_in_page(
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
    
    # Pair any text with amount
    item_lines = detect_text_lines(text_side)
    amount_line = detect_amount_text_lines(budget_side)
    
    grouped_items = group_aligned_bboxes((item_lines, amount_line))
    
    # Read text for each group
    budget_data = []
    for idx, (_item, _amount) in enumerate(grouped_items):
        item_text = read_texts([_item[0]])
        if _amount is None: # if have no amount
            if idx == 0: continue # skip first row if amount is None
            # Check for prefix
            prefix, _ = get_prefix_pattern(item_text)
            if prefix is None and budget_data:
                budget_data[-1]['name'] += item_text
            else: # is prefix
                budget_data.append({
                    'name': clean_text_prefix(item_text),
                    'amount': None
                })
            continue
        amount_text = read_texts([_amount[0]])
        cleaned_amount_text = re.sub(r"\D", "", amount_text).strip()
        amount = int(cleaned_amount_text) if re.search(r"\d", cleaned_amount_text) else 0
        
        # Check previous entry, if None; add text & amount
        if budget_data and budget_data[-1]['amount'] is None:
            budget_data[-1]['name'] += item_text
            budget_data[-1]['amount'] = amount
            continue
        budget_data.append({
            'name': clean_text_prefix(item_text),
            'amount': amount
        })
                
    return budget_data

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

def get_core_content_topic(
    text: str,
    threshold: float=0.8
) -> str|None:
    
    def get_similarity(s1, s2) -> float:
        score = fuzz.ratio(s1, s2) / 100 # RapidFuzz returns 0-100
        return score
    
    TOPIC_MATCH = [
        'วิสัยทัศน์', 'พันธกิจ', 'วัตถุประสงค์'
    ]
    TOPIC_INDEX = {
        'วิสัยทัศน์': 'vision', 
        'พันธกิจ': 'mission', 
        'วัตถุประสงค์': 'mission', 
    }
    
    # Clean text
    text = re.sub(r"[^\u0e00-\u0e59]", "", text).strip() # remove non-thai
    best_match = None
    highest_score = 0
    
    for topic in TOPIC_MATCH:
        score = get_similarity(text, topic)
        if score > highest_score and score >= threshold:
            highest_score = score
            best_match = topic
    if best_match:
        return TOPIC_INDEX.get(best_match, None)

def read_core_content_in_page(
    page: npt.NDArray,
    top_margin_percentage: float=0.03,
    topic_margin_threshold: int=12
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
    # Filtered only x1 with page width
    filted_x1 = sorted([
        x for x in all_x1 if x < (cropped_page.shape[1] * 0.4)
    ])
    header_diff = abs(filted_x1[0] - filted_x1[1]) if len(filted_x1) > 1 else 0
    x_split_point = header_diff + topic_margin_threshold + min(filted_x1)
    
    # Group data
    # TODO: make type alias global
    contents: List[Tuple[Tuple[npt.NDArray, tuple[int, int, int, int]], List[Any]]] = []
    current_group: Tuple[Tuple[npt.NDArray, Tuple[int, int, int, int]], List[Any]]|None = None
    for text_line in text_lines:
        _, bbox = text_line
        if bbox[0] < x_split_point: # x1 < split line
            if current_group:
                contents.append(current_group)
            current_group = (text_line, [])
            continue
        if current_group:
            current_group[1].append(text_line)
    if current_group:
        contents.append(current_group)
        
    result_data = {}
    for topic, text_lines in contents:
        # Read text from topic
        topic_text = read_texts([topic[0]])
        topic_key = get_core_content_topic(topic_text)
        if topic_key:
            result_data[topic_key] = read_texts([
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
    # Search for budget plan prefix
    budget_plan_matched = re.search(r"(7\.\d)\s(.+?)(?=$|\n)", extracted_text)
    if budget_plan_matched:
        result['budget_plan_prefix'] = budget_plan_matched.group(1)
    # Search for budget plan name
    budget_plan_matched = re.search(r"แผนงาน.+?(?=$|\n)", extracted_text)
    if budget_plan_matched:
        result['budget_plan_name'] = budget_plan_matched.group(0)
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