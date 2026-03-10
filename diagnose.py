"""
Run this ONCE to see exactly what column types + raw values monday.com returns.
Usage: python diagnose.py
"""
from monday_api import get_boards
import json

result = get_boards()
boards = result["data"]["boards"]

for board in boards:
    print(f"\n{'='*60}")
    print(f"BOARD: {board['name']}")
    print(f"{'='*60}")
    items = board["items_page"]["items"]
    if not items:
        print("  (no items)")
        continue
    # Show first 2 items with ALL column data
    for item in items[:2]:
        print(f"\n  Item: {item['name']}")
        for col in item["column_values"]:
            title = col["column"]["title"]
            ctype = col["column"]["type"]
            text  = col.get("text")
            value = col.get("value")
            print(f"    [{ctype:20s}] {title:30s} | text={repr(text)[:40]:42s} | value={repr(value)[:60]}")