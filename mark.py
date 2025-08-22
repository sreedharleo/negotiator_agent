import requests
import json

# Ollama server endpoint
url = "http://localhost:11434/api/generate"

# Prompt for testing
data = {
    "model": "llama3.1:8b",  # or "llama3.1:8b-instruct" depending on your pull
    "prompt": "You are a negotiation agent. Say hello to the seller.",
    "stream": False
}

response = requests.post(url, json=data)
print(response.json()["response"])
