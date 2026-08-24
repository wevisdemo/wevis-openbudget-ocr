from typing import Dict, List, Any
import os
import json
import pandas as pd

OBJ_DIR = 'output/obj'
OUT_DIR = 'output/core-content'

def extract_core_contents(data: Dict[str, Any]) -> pd.DataFrame:
    rows = []

    # Process Ministry (Top level)
    rows.append({
        "NAME": data.get("name"),
        "UNIT": "MINISTRY",
        "VISION": data.get("vision"),
        "MISSION": data.get("mission")
    })

    # Process Budgetary Units (Nested level)
    for unit in data.get("budgetray_units", []):
        rows.append({
            "NAME": unit.get("name"),
            "UNIT": "BUDGETARY_UNIT",
            "VISION": unit.get("vision"),
            "MISSION": unit.get("mission")
        })

    # Create and display DataFrame
    df = pd.DataFrame(rows)
    return df

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    for filename in os.listdir(OBJ_DIR):
        if not filename.endswith('.json'):
            continue
        with open(os.path.join(OBJ_DIR, filename), 'r') as f:
            data = json.load(f)
            
        df = extract_core_contents(data)
        df.to_csv(
            os.path.join(OUT_DIR, filename.replace('.json', '.csv')),
            index=False
        )

if __name__ == "__main__":
    main()