import requests

print("Gmoon Started!")

while True:
    user = input("You: ")

    payload = {
        "model": "qwen2.5:1.5b",
        "prompt": user,
        "stream": False
    }

    response = requests.post(
        "http://localhost:11434/api/generate",
        json=payload
    )

    answer = response.json()["response"]

    print("Gmoon:", answer)