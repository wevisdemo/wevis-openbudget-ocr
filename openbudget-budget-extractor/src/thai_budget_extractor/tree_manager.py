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
    page_num = item['page']
    
    if len(prefixes_stack) == 0:
      prefix, order = get_prefix_pattern(title)
      prefixes_stack.append((prefix, order))
      result_data.append({
          'name': title,
          'amount': amount_val,
          'page': page_num,
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
          'page': page_num,
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
          'page': page_num,
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
          'page': page_num,
          '_level': current_depth
      })
      continue

    # If no match in stack, treat as a new sub-level
    prefixes_stack.append((prefix, order))
    current_depth = len(prefixes_stack) - 1
    result_data.append({
        'name': title,
        'amount': amount_val,
        'page': page_num,
        '_level': current_depth
    })

  return result_data

def construct_tree_data(tree_data: List[Dict[str, Any]]) -> List[Dict]:
  # Assign _depth to each item
  tree_data = split_text_to_data(tree_data)

  result, path = [], {}

  # Dynamically grab the starting level from the first item (fallback to 0 if list is empty)
  root_level = tree_data[0]['_level'] if tree_data else 0
  for item in tree_data:
      node = dict(item, children=[])
      level = node.pop('_level')
      
      # If the level matches root_level, it's a root node
      if level == root_level:
          result.append(node)
      else:
          # Otherwise, append to the immediate parent
          path[level - 1]['children'].append(node)
          
      path[level] = node

  return result
  
def transform_budget_plan_data(outputs_data: List[Dict[str, str]]):
    grouped = {}
    
    for item in outputs_data:
        prefix = item["budget_plan_prefix"]
        name = item["budget_plan_name"]
        output = {
          "type": item.get('type'),
          "name": item.get('name'),
          "document": item.get('document'),
          "page": item.get('page'),
          "budget_details": item.get('budget_details')
        }
        
        if prefix not in grouped:
            grouped[prefix] = {
                "prefix": prefix,
                "name": name,
                "type": 'BUDGET_PLAN',
                "document": item.get('document'),
                "page": item.get('page'),
                "outputs": []
            }
        elif name is not None:
            grouped[prefix]["name"] = name
            
        grouped[prefix]["outputs"].append(output)
    
    # Normalize 7.1
    if "7.1" in grouped:
      grouped["7.1"]["name"] = "แผนงานบุคลากรภาครัฐ"
      grouped["7.1"]["outputs"] = []
        
    return list(grouped.values())

def get_text_and_depth(row):
  for i in range(1, 11+1):
    if row[f'name_{i}'] != '':
     return row[f'name_{i}'], i
  return '', None

def add_depth_and_text(budget_tree: pd.DataFrame) -> pd.DataFrame:
    assert all(
        col in budget_tree.columns for col in [
            f"name_{n}" for n in range(1, 11+1)
        ]
    )
    
    budget_tree[['_text', '_depth']] = budget_tree.apply(
      lambda row: get_text_and_depth(row),
        axis=1, result_type='expand'
    )
    
    return budget_tree
