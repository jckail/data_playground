import requests

def generate_fake_data():
    response = requests.post("http://0.0.0.0:8000/trigger_fake_data")
    return response.json()["message"]
