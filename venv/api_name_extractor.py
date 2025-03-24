import requests
import time
import json
import string

BASE_URL = "http://35.200.185.69:8000/v1/autocomplete?query="
OUTPUT_FILE = "three_names.json"
RATE_LIMIT_DELAY = 2.0  # Delay between batches (in seconds)
MAX_RETRIES = 3  # Max retries for failed requests
MAX_RESULTS = 10  # Maximum number of results per query
MAX_DEPTH = 3  # Maximum depth of recursion (e.g., 3-letter strings)
BATCH_SIZE = 10  # Number of queries to process in each batch

# Cache to store results of previously queried prefixes
cache = {}

def fetch_names(query):
    """Fetch names from API for a given query."""
    if query in cache:
        return cache[query]  # Return cached results if available

    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(BASE_URL + query)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                cache[query] = results  # Cache the results
                return results
            elif response.status_code == 429:
                print(f"Rate limit exceeded for query: {query}. Retrying...")
                retries += 1
                time.sleep(RATE_LIMIT_DELAY * (2 ** retries))  # Exponential backoff
            else:
                print(f"Error {response.status_code} for query: {query}. Retrying...")
                retries += 1
                time.sleep(RATE_LIMIT_DELAY * (2 ** retries))  # Exponential backoff
        except requests.RequestException as e:
            print(f"Request failed: {e}. Retrying...")
            retries += 1
            time.sleep(RATE_LIMIT_DELAY * (2 ** retries))  # Exponential backoff
    print(f"Max retries reached for query: {query}. Skipping...")
    return []

def explore_prefix(prefix, all_names, depth=1):
    """Recursively explore prefixes based on the number of results."""
    if depth > MAX_DEPTH:
        return  # Stop recursion if max depth is reached

    print(f"Querying: {prefix}")
    names = fetch_names(prefix)
    all_names.update(names)  # Add all returned names to the set

    # If the number of results is MAX_RESULTS, drill down further
    if len(names) == MAX_RESULTS:
        for letter in string.ascii_lowercase:
            new_prefix = prefix + letter
            explore_prefix(new_prefix, all_names, depth + 1)
    else:
        # If fewer than MAX_RESULTS, move to the next prefix
        return

def save_progress(all_names, file="progress.json"):
    """Save progress to a file."""
    with open(file, "w") as f:
        json.dump(list(all_names), f, indent=4)

def extract_all_names():
    """Extract all possible names using recursive prefix exploration."""
    all_names = set()  # Use a set to store unique names

    # Generate all single-letter and two-letter prefixes
    prefixes = list(string.ascii_lowercase)
    for first_letter in string.ascii_lowercase:
        for second_letter in string.ascii_lowercase:
            prefixes.append(first_letter + second_letter)

    # Process prefixes in batches
    for i in range(0, len(prefixes), BATCH_SIZE):
        batch = prefixes[i:i + BATCH_SIZE]  # Get the next batch of prefixes
        print(f"Processing batch: {batch}")

        for prefix in batch:
            explore_prefix(prefix, all_names)

        # Save progress after each batch
        save_progress(all_names, "progress.json")
        print(f"Progress: {min(i + BATCH_SIZE, len(prefixes))}/{len(prefixes)} prefixes processed.")

        # Respect rate limits by pausing between batches
        if i + BATCH_SIZE < len(prefixes):
            print(f"Waiting {RATE_LIMIT_DELAY} seconds before next batch...")
            time.sleep(RATE_LIMIT_DELAY)

    # Save final results to a file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(list(all_names), f, indent=4)

    print(f"Extraction complete. {len(all_names)} names saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_all_names()

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
