import requests
import time
import json
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
from queue import Queue
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

# Configuration
BASE_URL = "http://35.200.185.69:8000/v1/autocomplete?query="
OUTPUT_FILE = "autocomplete_names.json"
PROGRESS_FILE = "progress.json"
MAX_RETRIES = 5
MAX_THREADS = 3  # Conservative thread count to avoid rate limiting
MIN_DELAY = 1.5  # Minimum delay between requests (seconds)
MAX_DELAY = 5.0  # Maximum delay when backing off
REQUEST_TIMEOUT = 15
MAX_DEPTH = 3
BATCH_SAVE_INTERVAL = 60  # Save progress every 60 seconds

# Global state
cache = {}
cache_lock = Lock()
results_lock = Lock()
all_names = set()
request_queue = Queue()
rate_limit_semaphore = Semaphore(MAX_THREADS)
last_request_time = 0
request_counter = 0
rate_limit_hits = 0

def get_delay_factor():
    """Calculate dynamic delay factor based on recent rate limiting."""
    global rate_limit_hits
    base_delay = MIN_DELAY + (MAX_DELAY - MIN_DELAY) * min(rate_limit_hits / 10, 1.0)
    jitter = random.uniform(0.8, 1.2)  # Add some randomness
    return base_delay * jitter

def enforce_rate_limit():
    """Ensure we respect rate limits between requests."""
    global last_request_time
    current_time = time.time()
    elapsed = current_time - last_request_time
    delay_needed = max(0, get_delay_factor() - elapsed)
    
    if delay_needed > 0:
        time.sleep(delay_needed)
    
    last_request_time = time.time()

def fetch_names(query):
    """Fetch names from API with robust error handling."""
    global request_counter, rate_limit_hits
    
    # Check cache first
    with cache_lock:
        if query in cache:
            return cache[query]
    
    retries = 0
    while retries < MAX_RETRIES:
        try:
            with rate_limit_semaphore:
                enforce_rate_limit()
                response = requests.get(
                    BASE_URL + query,
                    timeout=REQUEST_TIMEOUT,
                    headers={'User-Agent': 'AutocompleteScraper/1.0'}
                )
                request_counter += 1
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    # Update cache
                    with cache_lock:
                        cache[query] = results
                    
                    return results
                
                elif response.status_code == 429:
                    rate_limit_hits += 1
                    backoff = min(2 ** retries * MIN_DELAY, MAX_DELAY)
                    logging.warning(f"Rate limited on {query}. Backing off for {backoff:.1f}s")
                    time.sleep(backoff)
                    retries += 1
                
                else:
                    logging.warning(f"HTTP {response.status_code} on {query}. Retry {retries + 1}/{MAX_RETRIES}")
                    time.sleep(get_delay_factor())
                    retries += 1
        
        except requests.exceptions.RequestException as e:
            logging.warning(f"Request failed on {query}: {str(e)}. Retry {retries + 1}/{MAX_RETRIES}")
            time.sleep(get_delay_factor())
            retries += 1
    
    logging.error(f"Max retries exceeded for query: {query}")
    return []

def process_prefix(prefix):
    """Process a prefix and potentially add deeper prefixes to queue."""
    names = fetch_names(prefix)
    
    with results_lock:
        all_names.update(names)
    
    # Only explore deeper if we got results and haven't hit max depth
    if names and len(prefix) < MAX_DEPTH:
        for letter in string.ascii_lowercase:
            new_prefix = prefix + letter
            request_queue.put(new_prefix)
    
    return len(names)

def worker():
    """Worker thread that processes prefixes from the queue."""
    while True:
        try:
            prefix = request_queue.get_nowait()
            try:
                process_prefix(prefix)
            except Exception as e:
                logging.error(f"Error processing {prefix}: {str(e)}")
            finally:
                request_queue.task_done()
        except:
            break

def save_progress():
    """Save current results to file."""
    with results_lock:
        progress_data = {
            'names': sorted(all_names),
            'cache': cache,
            'stats': {
                'requests': request_counter,
                'unique_names': len(all_names),
                'rate_limit_hits': rate_limit_hits,
                'last_saved': time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress_data, f, indent=2)
        logging.info(f"Progress saved. Names: {len(all_names)}, Requests: {request_counter}")

def load_progress():
    """Load previous progress from file if exists."""
    global all_names, cache, request_counter, rate_limit_hits
    
    try:
        with open(PROGRESS_FILE, 'r') as f:
            data = json.load(f)
            all_names.update(data.get('names', []))
            cache.update(data.get('cache', {}))
            stats = data.get('stats', {})
            request_counter = stats.get('requests', 0)
            rate_limit_hits = stats.get('rate_limit_hits', 0)
            logging.info(f"Loaded previous progress: {len(all_names)} names, {request_counter} requests")
    except (FileNotFoundError, json.JSONDecodeError):
        logging.info("No previous progress found, starting fresh")

def generate_initial_prefixes():
    """Generate all 1 and 2-character prefixes."""
    prefixes = list(string.ascii_lowercase)
    for first in string.ascii_lowercase:
        for second in string.ascii_lowercase:
            prefixes.append(first + second)
    return prefixes

def main():
    load_progress()
    
    # Initialize queue with prefixes not already in cache
    initial_prefixes = generate_initial_prefixes()
    for prefix in initial_prefixes:
        if prefix not in cache:
            request_queue.put(prefix)
    
    logging.info(f"Starting with {request_queue.qsize()} prefixes to process")
    
    # Start worker threads
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(worker) for _ in range(MAX_THREADS)]
        
        try:
            last_save = time.time()
            while True:
                # Check if all work is done
                if request_queue.empty() and all(f.done() for f in futures):
                    break
                
                # Periodically save progress
                if time.time() - last_save > BATCH_SAVE_INTERVAL:
                    save_progress()
                    last_save = time.time()
                
                time.sleep(1)
        
        except KeyboardInterrupt:
            logging.info("\nReceived interrupt. Finishing current tasks...")
        
        finally:
            # Final save
            save_progress()
            logging.info(f"Completed. Total names: {len(all_names)}, Total requests: {request_counter}")
            
            # Save final results
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(sorted(all_names), f, indent=2)

if __name__ == "__main__":
    main()


# import requests
# import time
# import json
# import string

# BASE_URL = "http://35.200.185.69:8000/v1/autocomplete?query="
# OUTPUT_FILE = "three_names.json"
# RATE_LIMIT_DELAY = 2.0  # Delay between batches (in seconds)
# MAX_RETRIES = 3  # Max retries for failed requests
# MAX_RESULTS = 10  # Maximum number of results per query
# MAX_DEPTH = 3  # Maximum depth of recursion (e.g., 3-letter strings)
# BATCH_SIZE = 10  # Number of queries to process in each batch

# # Cache to store results of previously queried prefixes
# cache = {}

# def fetch_names(query):
#     """Fetch names from API for a given query."""
#     if query in cache:
#         return cache[query]  # Return cached results if available

#     retries = 0
#     while retries < MAX_RETRIES:
#         try:
#             response = requests.get(BASE_URL + query)
#             if response.status_code == 200:
#                 data = response.json()
#                 results = data.get("results", [])
#                 cache[query] = results  # Cache the results
#                 return results
#             elif response.status_code == 429:
#                 print(f"Rate limit exceeded for query: {query}. Retrying...")
#                 retries += 1
#                 time.sleep(RATE_LIMIT_DELAY * (2 ** retries))  # Exponential backoff
#             else:
#                 print(f"Error {response.status_code} for query: {query}. Retrying...")
#                 retries += 1
#                 time.sleep(RATE_LIMIT_DELAY * (2 ** retries))  # Exponential backoff
#         except requests.RequestException as e:
#             print(f"Request failed: {e}. Retrying...")
#             retries += 1
#             time.sleep(RATE_LIMIT_DELAY * (2 ** retries))  # Exponential backoff
#     print(f"Max retries reached for query: {query}. Skipping...")
#     return []

# def explore_prefix(prefix, all_names, depth=1):
#     """Recursively explore prefixes based on the number of results."""
#     if depth > MAX_DEPTH:
#         return  # Stop recursion if max depth is reached

#     print(f"Querying: {prefix}")
#     names = fetch_names(prefix)
#     all_names.update(names)  # Add all returned names to the set

#     # If the number of results is MAX_RESULTS, drill down further
#     if len(names) == MAX_RESULTS:
#         for letter in string.ascii_lowercase:
#             new_prefix = prefix + letter
#             explore_prefix(new_prefix, all_names, depth + 1)
#     else:
#         # If fewer than MAX_RESULTS, move to the next prefix
#         return

# def save_progress(all_names, file="progress.json"):
#     """Save progress to a file."""
#     with open(file, "w") as f:
#         json.dump(list(all_names), f, indent=4)

# def extract_all_names():
#     """Extract all possible names using recursive prefix exploration."""
#     all_names = set()  # Use a set to store unique names

#     # Generate all single-letter and two-letter prefixes
#     prefixes = list(string.ascii_lowercase)
#     for first_letter in string.ascii_lowercase:
#         for second_letter in string.ascii_lowercase:
#             prefixes.append(first_letter + second_letter)

#     # Process prefixes in batches
#     for i in range(0, len(prefixes), BATCH_SIZE):
#         batch = prefixes[i:i + BATCH_SIZE]  # Get the next batch of prefixes
#         print(f"Processing batch: {batch}")

#         for prefix in batch:
#             explore_prefix(prefix, all_names)

#         # Save progress after each batch
#         save_progress(all_names, "progress.json")
#         print(f"Progress: {min(i + BATCH_SIZE, len(prefixes))}/{len(prefixes)} prefixes processed.")

#         # Respect rate limits by pausing between batches
#         if i + BATCH_SIZE < len(prefixes):
#             print(f"Waiting {RATE_LIMIT_DELAY} seconds before next batch...")
#             time.sleep(RATE_LIMIT_DELAY)

#     # Save final results to a file
#     with open(OUTPUT_FILE, "w") as f:
#         json.dump(list(all_names), f, indent=4)

#     print(f"Extraction complete. {len(all_names)} names saved to {OUTPUT_FILE}")

# if __name__ == "__main__":
#     extract_all_names()

# import requests
# import time
# import json
# import string

# BASE_URL = "http://35.200.185.69:8000/v1/autocomplete?query="
# OUTPUT_FILE = "trial_names.json"
# RATE_LIMIT_DELAY = 0.5  # Delay between requests (in seconds)
# MAX_RETRIES = 3  # Max retries for failed requests

# def fetch_names(query):
#     """Fetch names from API for a given query."""
#     retries = 0
#     while retries < MAX_RETRIES:
#         try:
#             response = requests.get(BASE_URL + query)
#             if response.status_code == 200:
#                 data = response.json()
#                 return data.get("results", [])  # Extract the "results" list
#             else:
#                 print(f"Error {response.status_code} for query: {query}. Retrying...")
#                 retries += 1
#                 time.sleep(RATE_LIMIT_DELAY)
#         except requests.RequestException as e:
#             print(f"Request failed: {e}. Retrying...")
#             retries += 1
#             time.sleep(RATE_LIMIT_DELAY)
#     print(f"Max retries reached for query: {query}. Skipping...")
#     return []

# def extract_all_names():
#     """Extract all possible names using systematic queries."""
#     all_names = set()  # Use a set to store unique names

#     # Querying all single letters (a-z)
#     for letter in string.ascii_lowercase:
#         print(f"Querying: {letter}")
#         names = fetch_names(letter)
#         all_names.update(names)  # Add all returned names
#         time.sleep(RATE_LIMIT_DELAY)  # Respect rate limits

#     # Querying all two-letter combinations (aa, ab, ac, ..., zz)
#     for first_letter in string.ascii_lowercase:
#         for second_letter in string.ascii_lowercase:
#             query = first_letter + second_letter
#             print(f"Querying: {query}")
#             names = fetch_names(query)
#             all_names.update(names)  # Add all returned names
#             time.sleep(RATE_LIMIT_DELAY)  # Respect rate limits

#     # Save results to a file
#     with open(OUTPUT_FILE, "w") as f:
#         json.dump(list(all_names), f, indent=4)

#     print(f"Extraction complete. {len(all_names)} names saved to {OUTPUT_FILE}")

# if __name__ == "__main__":
#     extract_all_names()
