import requests
import time
import json
import string

API_BASE = "http://35.200.185.69:8000/v2/autocomplete?query="
OUTPUT_FILE = "v2_names.json"
RATE_LIMIT_DELAY = 1.2
MAX_RETRIES = 5

def fetch_names(query):
    for retry in range(MAX_RETRIES):
        try:
            response = requests.get(API_BASE + query, timeout=10)
            if response.status_code == 200:
                return response.json().get("results", [])
            elif response.status_code == 429:
                wait = min(2 ** retry, 10) * RATE_LIMIT_DELAY
                print(f"Rate limited on '{query}'. Waiting {wait:.1f}s...")
                time.sleep(wait)
            else:
                print(f"HTTP {response.status_code} on '{query}'. Retry {retry+1}/{MAX_RETRIES}")
                time.sleep(RATE_LIMIT_DELAY)
        except requests.RequestException as e:
            print(f"Request failed on '{query}': {e}. Retry {retry+1}/{MAX_RETRIES}")
            time.sleep(RATE_LIMIT_DELAY)
    print(f"Max retries exceeded for '{query}'")
    return []

def main():
    results = set()
    chars = string.ascii_lowercase + string.digits
    
    # Single character queries
    for c in chars:
        print(f"Querying '{c}'")
        results.update(fetch_names(c))
        time.sleep(RATE_LIMIT_DELAY)
    
    # Two character queries
    for c1 in chars:
        for c2 in chars:
            query = c1 + c2
            print(f"Querying '{query}'")
            results.update(fetch_names(query))
            time.sleep(RATE_LIMIT_DELAY)
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(sorted(results), f, indent=2)
    print(f"Saved {len(results)} names to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()