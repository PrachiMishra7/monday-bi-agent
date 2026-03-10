import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MONDAY_API_KEY")
URL = "https://api.monday.com/v2"

HEADERS = {
    "Authorization": API_KEY,
    "Content-Type": "application/json",
    "API-Version": "2024-01"
}


def build_query(cursor=None):
    """Build paginated GraphQL query for both boards."""
    cursor_arg = f', cursor: "{cursor}"' if cursor else ""
    return f"""
    {{
      boards(limit: 10) {{
        id
        name
        items_page(limit: 100{cursor_arg}) {{
          cursor
          items {{
            id
            name
            column_values {{
              column {{
                title
                type
              }}
              text
              value
            }}
          }}
        }}
      }}
    }}
    """


def get_all_items_for_board(board_data):
    """Paginate through all items in a board."""
    all_items = list(board_data["items_page"]["items"])
    cursor = board_data["items_page"].get("cursor")
    board_id = board_data["id"]

    while cursor:
        paginated_query = f"""
        {{
          boards(ids: [{board_id}]) {{
            id
            name
            items_page(limit: 100, cursor: "{cursor}") {{
              cursor
              items {{
                id
                name
                column_values {{
                  column {{
                    title
                    type
                  }}
                  text
                  value
                }}
              }}
            }}
          }}
        }}
        """
        try:
            resp = requests.post(URL, json={"query": paginated_query}, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            result = resp.json()

            if "errors" in result:
                break

            page_board = result["data"]["boards"][0]
            page_items = page_board["items_page"]["items"]
            all_items.extend(page_items)
            cursor = page_board["items_page"].get("cursor")

        except Exception:
            break

    return all_items


def get_boards():
    """
    Fetch all boards and items from monday.com with pagination and error handling.
    Returns a dict with 'data', 'error', and 'boards_fetched' keys.
    """
    if not API_KEY:
        return {
            "data": None,
            "error": "MONDAY_API_KEY not set in environment variables.",
            "boards_fetched": []
        }

    try:
        response = requests.post(
            URL,
            json={"query": build_query()},
            headers=HEADERS,
            timeout=15
        )
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            return {
                "data": None,
                "error": f"monday.com API error: {result['errors'][0].get('message', 'Unknown error')}",
                "boards_fetched": []
            }

        # Paginate each board
        boards = result["data"]["boards"]
        for board in boards:
            board["items_page"]["items"] = get_all_items_for_board(board)

        boards_fetched = [b["name"] for b in boards]

        return {
            "data": result["data"],
            "error": None,
            "boards_fetched": boards_fetched
        }

    except requests.exceptions.Timeout:
        return {
            "data": None,
            "error": "Request timed out. monday.com API may be slow — please retry.",
            "boards_fetched": []
        }
    except requests.exceptions.ConnectionError:
        return {
            "data": None,
            "error": "Could not connect to monday.com. Check your internet connection.",
            "boards_fetched": []
        }
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        if status == 401:
            return {"data": None, "error": "Invalid monday.com API key (401 Unauthorized).", "boards_fetched": []}
        elif status == 429:
            return {"data": None, "error": "Rate limited by monday.com API. Please wait and retry.", "boards_fetched": []}
        return {"data": None, "error": f"HTTP error {status} from monday.com.", "boards_fetched": []}
    except Exception as e:
        return {
            "data": None,
            "error": f"Unexpected error fetching data: {str(e)}",
            "boards_fetched": []
        }