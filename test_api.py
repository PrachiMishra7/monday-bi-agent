"""
Test script for monday.com API connection and data extraction.
Run: python test_api.py
"""

import json
from monday_api import get_boards
from agent import extract_all_metrics


def test_connection():
    print("=" * 60)
    print("TEST 1: API Connection")
    print("=" * 60)

    result = get_boards()

    if result["error"]:
        print(f"❌ FAILED: {result['error']}")
        return None

    print(f"✅ Connected successfully!")
    print(f"   Boards fetched: {result['boards_fetched']}")
    return result


def test_board_data(result):
    print("\n" + "=" * 60)
    print("TEST 2: Board Data Structure")
    print("=" * 60)

    boards = result["data"]["boards"]
    for board in boards:
        item_count = len(board["items_page"]["items"])
        print(f"✅ Board: '{board['name']}' — {item_count} items")

        if item_count > 0:
            sample = boards[0]["items_page"]["items"][0]
            col_titles = [c["column"]["title"] for c in sample.get("column_values", [])]
            print(f"   Columns: {col_titles[:8]}{'...' if len(col_titles) > 8 else ''}")


def test_metrics(result):
    print("\n" + "=" * 60)
    print("TEST 3: Metric Extraction")
    print("=" * 60)

    try:
        metrics = extract_all_metrics(result["data"])

        d = metrics["deals"]
        w = metrics["work_orders"]
        cb = metrics["cross_board"]

        print(f"✅ Deals extracted: {d['total_count']}")
        print(f"   Pipeline value:  ${d['total_pipeline_value']:,.2f}")
        print(f"   Won deals:       {d['won_count']} (${d['won_value']:,.2f})")
        print(f"   Win rate:        {(d['won_count']/d['total_count']*100 if d['total_count'] else 0):.1f}%")
        print(f"   Sectors:         {list(d['by_sector'].keys())[:5]}")

        print(f"\n✅ Work Orders extracted: {w['total_count']}")
        print(f"   Total revenue:   ${w['total_revenue']:,.2f}")
        print(f"   Completed:       {w['completed_count']}")
        print(f"   Sectors:         {list(w['by_sector'].keys())[:5]}")

        print(f"\n✅ Cross-board:")
        print(f"   Combined revenue: ${cb['combined_revenue']:,.2f}")
        print(f"   Shared sectors:   {cb['sectors_in_both']}")

        if metrics["quality_issues"]:
            print(f"\n⚠️  Data quality issues ({len(metrics['quality_issues'])}):")
            for issue in metrics["quality_issues"][:5]:
                print(f"   - {issue}")
        else:
            print("\n✅ No data quality issues found.")

    except Exception as e:
        print(f"❌ Metric extraction failed: {e}")
        import traceback
        traceback.print_exc()


def test_agent(result):
    print("\n" + "=" * 60)
    print("TEST 4: Agent Response")
    print("=" * 60)

    from agent import ask_agent
    test_question = "Give me a quick overview of where we stand."

    print(f"Question: '{test_question}'")
    print("Waiting for LLM response...\n")

    try:
        answer = ask_agent(test_question, result)
        print(answer[:600] + ("..." if len(answer) > 600 else ""))
        print("\n✅ Agent responded successfully.")
    except Exception as e:
        print(f"❌ Agent failed: {e}")


if __name__ == "__main__":
    result = test_connection()
    if result:
        test_board_data(result)
        test_metrics(result)
        test_agent(result)

    print("\n" + "=" * 60)
    print("All tests complete.")
    print("=" * 60)