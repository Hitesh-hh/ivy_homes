import requests
import time
import json
import string
from datetime import datetime

API_BASE = "http://35.200.185.69:8000/v3/autocomplete?query="
OUTPUT_FILE = "v3_names.json"
PROGRESS_FILE = "v3_progress.json"
RATE_LIMIT_DELAY = 0.75  # 80 requests/minute (60/80 = 0.75s)
MAX_RETRIES = 3
CHAR_SET = string.ascii_lowercase + '+-. '  

# Track rate limiting
last_request_time = 0
request_count = 0
minute_start = time.time()

def enforce_rate_limit():
    global last_request_time, request_count, minute_start
    
    # Reset counter every minute
    if time.time() - minute_start > 60:
        request_count = 0
        minute_start = time.time()
    
    # Calculate required delay
    elapsed = time.time() - last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    
    last_request_time = time.time()
    request_count += 1

def fetch_names(query):
    for retry in range(MAX_RETRIES):
        try:
            enforce_rate_limit()
            response = requests.get(API_BASE + query, timeout=15)
            
            if response.status_code == 200:
                return response.json().get("results", [])
            elif response.status_code == 429:
                backoff = min(2 ** retry * RATE_LIMIT_DELAY, 10)
                print(f"{datetime.now().strftime('%H:%M:%S')} - Rate limited on '{query}'. Waiting {backoff:.1f}s...")
                time.sleep(backoff)
            else:
                print(f"{datetime.now().strftime('%H:%M:%S')} - HTTP {response.status_code} on '{query}'. Retry {retry+1}/{MAX_RETRIES}")
                time.sleep(RATE_LIMIT_DELAY)
        except requests.RequestException as e:
            print(f"{datetime.now().strftime('%H:%M:%S')} - Request failed on '{query}': {e}. Retry {retry+1}/{MAX_RETRIES}")
            time.sleep(RATE_LIMIT_DELAY)
    
    print(f"{datetime.now().strftime('%H:%M:%S')} - Max retries exceeded for '{query}'")
    return []

def save_progress(results):
    progress = {
        'results': sorted(results),
        'timestamp': datetime.now().isoformat(),
        'request_count': request_count
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def main():
    results = set()
    
    try:
        # Load progress if exists
        try:
            with open(PROGRESS_FILE, 'r') as f:
                progress = json.load(f)
                results.update(progress.get('results', []))
                print(f"Resumed progress with {len(results)} existing names")
        except FileNotFoundError:
            pass
        
        # Single character queries (28)
        for c in CHAR_SET:
            if c == ' ':  # Handle space character
                query = '%20'
            else:
                query = c
                
            print(f"{datetime.now().strftime('%H:%M:%S')} - Querying '{c}'")
            results.update(fetch_names(query))
            save_progress(results)
        
        # Two character queries (28x28 = 784)
        for i, c1 in enumerate(CHAR_SET):
            for c2 in CHAR_SET:
                query = (c1 + c2).replace(' ', '%20')
                print(f"{datetime.now().strftime('%H:%M:%S')} - Querying '{c1}{c2}' ({i+1}/28)")
                results.update(fetch_names(query))
                
                # Save progress every 25 queries
                if len(results) % 25 == 0:
                    save_progress(results)
    
    except KeyboardInterrupt:
        print("\nScript interrupted. Saving progress...")
    
    finally:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(sorted(results), f, indent=2)
        print(f"Saved {len(results)} names to {OUTPUT_FILE}")
        print(f"Total API requests made: {request_count}")

if __name__ == "__main__":
    main()


# import requests
# import time
# import json
# import string

# API_BASE = "http://35.200.185.69:8000/v3/autocomplete?query="
# OUTPUT_FILE = "v3_names.json"
# RATE_LIMIT_DELAY = 0.5
# MAX_RETRIES = 5

# def fetch_names(query):
#     for retry in range(MAX_RETRIES):
#         try:
#             response = requests.get(API_BASE + query, timeout=10)
#             if response.status_code == 200:
#                 return response.json().get("results", [])
#             elif response.status_code == 429:
#                 wait = min(2 ** retry, 10) * RATE_LIMIT_DELAY
#                 print(f"Rate limited on '{query}'. Waiting {wait:.1f}s...")
#                 time.sleep(wait)
#             else:
#                 print(f"HTTP {response.status_code} on '{query}'. Retry {retry+1}/{MAX_RETRIES}")
#                 time.sleep(RATE_LIMIT_DELAY)
#         except requests.RequestException as e:
#             print(f"Request failed on '{query}': {e}. Retry {retry+1}/{MAX_RETRIES}")
#             time.sleep(RATE_LIMIT_DELAY)
#     print(f"Max retries exceeded for '{query}'")
#     return []

# def main():
#     results = set()
#     chars = string.ascii_lowercase + '+-'
    
#     # Single character queries
#     for c in chars:
#         print(f"Querying '{c}'")
#         results.update(fetch_names(c))
#         time.sleep(RATE_LIMIT_DELAY)
    
#     # Two character queries
#     for c1 in chars:
#         for c2 in chars:
#             query = c1 + c2
#             print(f"Querying '{query}'")
#             results.update(fetch_names(query))
#             time.sleep(RATE_LIMIT_DELAY)
    
#     with open(OUTPUT_FILE, "w") as f:
#         json.dump(sorted(results), f, indent=2)
#     print(f"Saved {len(results)} names to {OUTPUT_FILE}")

# if __name__ == "__main__":
#     main()