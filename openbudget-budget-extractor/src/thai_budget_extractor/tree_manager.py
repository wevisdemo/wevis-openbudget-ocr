from typing import List, Dict, Any
import re
import pandas as pd
import numpy as np
from .budget_text_manager import get_prefix_pattern
from .constants import BUDGET_TREE_DEFAULT_COLUMNS


def split_tree_to_data(input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
      # First level is OUTPUT/PROJECT
      output_type = 'PROJECT' if 'โครงการ' in title else 'OUTPUT'
      result_data.append({
          'name': title,
          'type': output_type,
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
          'type': 'FISCAL_YEAR_BUDGET',
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
          'type': 'BUDGET_DETAIL',
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
          'type': 'BUDGET_DETAIL',
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
        'type': 'BUDGET_DETAIL',
        'amount': amount_val,
        'page': page_num,
        '_level': current_depth
    })

  return result_data

def construct_tree_data(tree_data: List[Dict[str, Any]]) -> List[Dict]:
  # Assign _depth to each item
  tree_data = split_tree_to_data(tree_data)

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
  
def transform_budget_plan_data(outputs_data: List[Dict[str, Any]]):
    grouped = {}
    
    for item in outputs_data:
        prefix = item["budget_plan_prefix"]
        name = item["budget_plan_name"]
        amount = item["budget_plan_amount"]
        outputs: List[Dict[str, Any]] = item.get('outputs', []) # type: ignore
        
        if prefix not in grouped:
            grouped[prefix] = {
                "prefix": prefix,
                "name": name,
                "type": 'BUDGET_PLAN',
                "amount": amount,
                "page": item.get('page'),
                "outputs": outputs
            }
            continue
        elif name is not None:
            grouped[prefix]["name"] = name
            
        grouped[prefix]["outputs"].extend(outputs)
    
    # Normalize 7.1
    if "7.1" in grouped:
      grouped["7.1"]["name"] = "แผนงานบุคลากรภาครัฐ"
      budget_detail = grouped["7.1"].get("outputs", [{}])[0]
      grouped["7.1"]["outputs"] = budget_detail.get('children')
        
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

def convert_budget_dict_to_df(data: Dict[str, Any]) -> pd.DataFrame:
    columns = BUDGET_TREE_DEFAULT_COLUMNS
    
    def traverse(node, depth, current_names):
        if not isinstance(node, dict):
            return []
            
        prefix = node.get("prefix", "")
        name = node.get("name", "")
        full_name = f"{prefix} {name}".strip() if prefix else name
        
        names = current_names.copy()
        if depth <= 11:
            names[f"name_{depth}"] = full_name
            
        row = {col: "" for col in columns}
        row.update(names)
        
        row["budget_type"] = node.get("type", "")
        row["amount"] = node.get("amount", "")
        row["document"] = node.get("document", "")
        row["page"] = node.get("page", "")
        row["error_message"] = node.get("error_message", "")
        
        # Handle fiscal_year
        row["fiscal_year"] = node.get("fiscal_year", "")
        row["fiscal_year_end"] = node.get("fiscal_year_end", "")
        if re.search(r"^ปี\s?25\d{2}", full_name):
            years = re.findall(r"25\d{2}", full_name)
            row["fiscal_year"] = years[0].strip()
            row["fiscal_year_end"] = years[-1].strip()
        
        rows = [row]
        
        for val in node.values():
            if isinstance(val, dict) and "name" in val:
                rows.extend(traverse(val, depth + 1, names))
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and "name" in item:
                        rows.extend(traverse(item, depth + 1, names))
                        
        return rows

    flat_data = traverse(data, 1, {})
    
    # Replace consecutive duplicates in column 'name_X' with empty string
    result_tree_df = pd.DataFrame(flat_data, columns=columns)
    for i in range(1, 11+1):
        result_tree_df.loc[result_tree_df[f"name_{i}"] == result_tree_df[f"name_{i}"].shift(), f"name_{i}"] = ''
        
    # Fill in document
    result_tree_df.loc[:, 'document'] = result_tree_df['document'].replace("", np.nan)
    result_tree_df['document'] = result_tree_df['document'].ffill()
    
    return result_tree_df