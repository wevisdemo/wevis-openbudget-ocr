from typing import List, Dict, Any
import re
import pandas as pd
from .budget_text_manager import get_prefix_pattern
from .constants import BUDGET_TREE_DEFAULT_COLUMNS


def split_text_to_data(input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
  result_data = []
  current_depth = 0

  # Stack now stores tuples of (pattern, order)
  prefixes_stack = []

  for item in input_data:
    title = item['name']
    amount_val = item['amount']
    
    if len(prefixes_stack) == 0:
      prefix, order = get_prefix_pattern(title)
      prefixes_stack.append((prefix, order))
      result_data.append({
          'name': title,
          'amount': amount_val,
          '_level': current_depth
      })
      continue

    if re.search("^วงเงินทั้งสิ้น", title): # Skip start fiscal year entry
      continue
    if re.search("^เงินนอกงบประมาณ", title): # Skip value outside budget
      continue
    # Check for fiscal year entry to stay in the same depth
    if re.search(r"^ปี\s?25\d{2}", title):
      result_data.append({
          'name': title,
          'amount': amount_val,
          '_level': current_depth
      })
      continue

    prefix, order = get_prefix_pattern(title)
    prev_prefix, prev_order = prefixes_stack[-1]

    # Same level continuation: Same pattern and order is greater (or un-ordered item)
    if prefix == prev_prefix and (order in (0, None) or prev_order in (0, None) or order > prev_order):
      prefixes_stack[-1] = (prefix, order)
      result_data.append({
          'name': title,
          'amount': amount_val,
          '_level': current_depth
      })
      continue

    # Step back or different pattern: search stack from top to bottom for a matching parent
    match_idx = -1
    for i in range(len(prefixes_stack) - 1, -1, -1):
      p, o = prefixes_stack[i]
      if p == prefix and (order in (0, None) or o in (0, None) or order > o):
        match_idx = i
        break

    if match_idx != -1:
      # Found parent level, step back and pop outer levels
      prefixes_stack = prefixes_stack[:match_idx + 1]
      prefixes_stack[-1] = (prefix, order)
      current_depth = match_idx
      result_data.append({
          'name': title,
          'amount': amount_val,
          '_level': current_depth
      })
      continue

    # If no match in stack, treat as a new sub-level
    prefixes_stack.append((prefix, order))
    current_depth = len(prefixes_stack) - 1
    result_data.append({
        'name': title,
        'amount': amount_val,
        '_level': current_depth
    })

  return result_data

def construct_tree_df(
    tree_data: List[Dict[str, Any]],
    base_depth:int = 0
) -> pd.DataFrame:
    
    # Assign _depth to each item
    tree_dict = split_text_to_data(tree_data)
    
    # Add name_X
    for item in tree_dict:
        depth = item.get('_level', 0) + base_depth
        depth = depth if depth <= 11 else 11
        item[f'name_{depth}'] = item.get('name')
    
    # Construct df
    df = pd.DataFrame(tree_dict)
    # Add & Reindex to default columns
    df = df.reindex(columns=BUDGET_TREE_DEFAULT_COLUMNS, fill_value='')
    
    return df