from typing import List, Dict, Tuple, Any, Optional
import numpy.typing as npt
import re
from .constants import PREFIX_PATTERNS

def clean_text_prefix(text: str) -> str:
    text = re.sub(r"(\(\d+\))([\u0e00-\u0e44].*)", r"\g<1> \g<2>", text)
    text = re.sub(r"^(\d+\))([\u0e00-\u0e44].*)", r"\g<1> \g<2>", text)
    text = re.sub(r"(.*[\u0e00-\u0e44])(\d+)ล้านบาท(.*)", r"\g<1> \g<2> ล้านบาท \g<3>", text)
    return text.strip()

def get_prefix_pattern(text: str) -> Tuple[str|None, int|None]:
  # Get text and extract prefix pattern and order of the prefix
  text = clean_text_prefix(text)
  for pattern, order in PREFIX_PATTERNS:
    match = re.match(pattern, text)
    if match:
      if order is None:
        return pattern, 0
      return pattern, int(match.group(order))
  return None, None

def normalize_prefixes_text(text: str) -> str:
    # Fix prefix
    text = re.sub(r"(?<!\.)\(?(\d+)\)?\s?(?=เงิน|ค่า)", r"(\g<1>) ", text)
    text = re.sub(r"(\d+\.)\s(\d+)", r" \g<1>\g<2>", text)
    text = re.sub(r"(\d+)[\u0e01-\u0e59]", r"\g<1> ", text)
    
    # Normalize text patterns to be consistent
    text = text.strip()
    text = re.sub(r"(?<=\d)\)(\s+)?", ") ", text)
    text = re.sub(r"ปี(\s+)?25", r"ปี 25", text)
    text = re.sub(r"(\s+)?(\d)\s+?ล้านบาท", r" \g<2> ล้านบาท", text)

    # Clean space
    text = re.sub(r"\s+", r" ", text)
    return text

def is_prefix(text: str) -> bool:
    check_list = [
        re.search(r"^\(?\d", text),
        re.search(r"^ปี\s?25", text),
        re.search(r"^วงเงิน", text),
        re.search(r"^เงินนอกงบ", text),
    ]
    return any([_ is not None for _ in check_list])

def split_pair_budget_amount(
    budget_items_texts: str,
    budget_amounts_texts: str,
) -> List[Dict[str, Any]]:
    
    # Process amount_queue
    amount_queue = []
    for value_str in budget_amounts_texts.splitlines():
        matched_value = re.search(r"(\d{1,3}(\,\d{3})+)", value_str)
        if not matched_value:
            continue
        amount_str = matched_value.group(1)
        amount_queue.append(int(re.sub(r"\,", "", amount_str).strip()))
    
    # Process budget_items_texts
    skip_pttrn = r"^รายละเอียดงบ.+?รายจ่าย"
    item_name_list = []
    item_name = ""
    for line in budget_items_texts.splitlines():
        if re.search(skip_pttrn, line):
            continue
        
        if not is_prefix(line):
            item_name += line.strip()
            continue
        
        # Found new topic
        item_name_list.append(item_name)
        item_name = normalize_prefixes_text(line)
    
    # Fill missing entry
    if len(amount_queue) > len(item_name_list):
        item_name_list += [""] * (len(amount_queue) - len(item_name_list))
    elif len(item_name_list) > len(amount_queue):
        amount_queue += [0] * (len(item_name_list) - len(amount_queue))
    result = [
        {'name': _itm, 'amount': _amt} for _itm, _amt in zip(item_name_list, amount_queue)
    ]
    return result

def group_aligned_bboxes(
    data: Tuple[List[Tuple[npt.NDArray, Tuple[int, int, int, int]]], List[Tuple[npt.NDArray, Tuple[int, int, int, int]]]], 
    overlap_threshold: float = 0.5
) -> List[Tuple[Tuple[npt.NDArray, Tuple[int, int, int, int]], Optional[Tuple[npt.NDArray, Tuple[int, int, int, int]]]]]:
    
    left_data, right_data = data
    
    left = sorted(left_data, key=lambda b: b[1][1])
    right = sorted(right_data, key=lambda b: b[1][1])
    
    grouped = []
    i, j = 0, 0
    
    while i < len(left) and j < len(right):
        l_item, r_item = left[i], right[j]
        l_box, r_box = l_item[1], r_item[1]
        
        y_top = max(l_box[1], r_box[1])
        y_bottom = min(l_box[3], r_box[3])
        overlap = max(0, y_bottom - y_top)
        
        h_l = l_box[3] - l_box[1]
        h_r = r_box[3] - r_box[1]
        min_h = max(min(h_l, h_r), 1e-5) 
        
        if (overlap / min_h) >= overlap_threshold:
            grouped.append((l_item, r_item))
            i += 1
            j += 1
        elif l_box[1] < r_box[1]:
            grouped.append((l_item, None))
            i += 1
        else:
            j += 1
            
    while i < len(left):
        grouped.append((left[i], None))
        i += 1
        
    return grouped