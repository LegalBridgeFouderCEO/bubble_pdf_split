import requests

url = "http://127.0.0.1:8000/run"
data = {"input": "Bonjour Bubble"}
response = requests.post(url, json=data)
print(response.json())
