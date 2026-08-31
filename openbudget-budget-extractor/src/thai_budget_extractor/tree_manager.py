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

# TODO: remove this function
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
  
def rearrange_budget_plan_chunks(df: pd.DataFrame):
    df_work = add_depth_and_text(df.fillna(''))
    
    # Identify the least depth (which acts as the chunk header)
    min_depth = df_work['_depth'].min()
    
    # Identify rows that are chunk headers
    header_mask = df_work['_depth'] == min_depth
    
    # Extract the prefix (e.g., '7.1', '7.2') from the '_text' column of header rows
    # .str.split().str[0] will take the first token (split by space)
    df_work.loc[header_mask, 'prefix'] = df_work.loc[header_mask]['_text'].apply(
      lambda text: text.split(' ')[0]
    )
    
    # Forward-fill the prefix down the rows to group detail rows with their header
    df_work['group'] = df_work['prefix'].ffill()
    
    merged_chunks = []
    
    # Group the dataframe by the prefix (e.g., all 7.2 rows are now in one group)
    for group_name, group_df in df_work.groupby('group', sort=False):
        
        # Separate the group into Headers and Detail Rows
        headers = group_df[group_df['_depth'] == min_depth]
        details = group_df[group_df['_depth'] > min_depth]
        
        if not headers.empty:
            # Find the index of the header row with the maximum length in '_text'
            longest_idx = headers['_text'].str.contains("แผนงาน").idxmin()
            best_header = headers.loc[[longest_idx]]
            
            # Reconstruct the chunk: keep only the longest header, followed by all details
            merged = pd.concat([best_header, details])
            merged_chunks.append(merged)
        else:
            merged_chunks.append(group_df)
            
    # Combine all chunks back into a single DataFrame and drop temporary columns
    final_df = pd.concat(
      merged_chunks
    ).drop(columns=['prefix', 'group', '_text', '_depth']).reset_index(drop=True)
    
    return final_df
  
def tree_df_to_nested_dict(df: pd.DataFrame) -> List[Dict[str, Any]]:
    result = []
    stack = []
    
    for row in df.to_dict('records'):
        depth, name = None, None
        
        for i in range(1, 12):
            col = f'name_{i}'
            if col in row and pd.notna(row[col]) and str(row[col]).strip() != '':
                depth = i
                name = row[col]
                break
                
        if depth is None:
            continue
            
        node = {
            "name": name,
            "amount": row.get("amount"),
            "document": row.get("document"),
            "page": row.get("page"),
            "children": []
        }
        
        while stack and stack[-1][0] >= depth:
            stack.pop()
            
        if not stack:
            result.append(node)
        else:
            stack[-1][1]["children"].append(node)
            
        stack.append((depth, node))
        
    return result