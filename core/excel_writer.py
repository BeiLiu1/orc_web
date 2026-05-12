import os
import pandas as pd


def save_excel(data, path):

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    if "result" in data and "rows" in data["result"]:
        df = pd.DataFrame(data["result"]["rows"])
    elif "red" in data:
        rows = []
        for color, v in data.items():
            rows.append({
                "颜色": color,
                "含税金额": v.get("amount_total", 0),
                "税费": v.get("tax_total", 0)
            })
        df = pd.DataFrame(rows)
    else:
        raise ValueError("Unknown excel data format")

    df.to_excel(path, index=False)

    print(f"Excel: {path}")