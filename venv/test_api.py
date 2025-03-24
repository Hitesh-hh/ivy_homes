import requests

BASE_URL = "http://35.200.185.69:8000/v1/autocomplete?query="

def test_api(query):
    response = requests.get(BASE_URL + query)
    print(f"Query: {query}")
    print(f"Response: {response.json() if response.status_code == 200 else response.text}")

test_api("a")
