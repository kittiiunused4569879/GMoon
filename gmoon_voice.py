import speech_recognition as sr
import requests
import time
import subprocess
from googlesearch import search
import os
import webbrowser
from datetime import datetime
import cv2
import base64
import json
import threading

MODEL = "qwen2.5:1.5b"
VISION_MODEL = "llava"
OLLAMA_URL = "http://localhost:11434/api/generate"

WAKE_WORD = "hey gmoon"

CAMERA_ENABLED = True
CAMERA_INDEX = 0
CAMERA_CHECK_SECONDS = 30
CAMERA_LOG_FILE = "camera_log.jsonl"

recognizer = sr.Recognizer()


def speak(text):
    if not text:
        return

    print("Speaking:", text)
    safe_text = text.replace("'", "''")

    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$speak.Rate = 0; "
        "$speak.Volume = 100; "
        f"$speak.Speak('{safe_text}');"
    )

    try:
        subprocess.run(["powershell", "-Command", command], shell=False)
    except Exception as e:
        print("Speech error:", e)


def save_chat(user, bot):
    try:
        with open("conversation.txt", "a", encoding="utf-8") as file:
            file.write(f"\nYou: {user}\n")
            file.write(f"Gmoon: {bot}\n")
    except Exception as e:
        print("Save error:", e)


def google_search(query):
    try:
        results = []
        for url in search(query, num_results=2):
            results.append(url)
        return "\n".join(results)
    except Exception as e:
        print("Google search error:", e)
        return ""


def frame_to_base64(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    return base64.b64encode(buffer).decode("utf-8")


def analyze_camera_frame(frame):
    image_b64 = frame_to_base64(frame)

    prompt = """
Look at this camera image and describe only visible facts.

Mention:
- whether a person is present
- what the person appears to be doing
- cooking, cleaning, washing vessels, eating, smoking, sitting, walking
- visible objects
- do not guess identity
- do not make accusations
- keep it short
"""

    payload = {
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print("Camera vision error:", e)
        return ""


def save_camera_log(summary):
    event = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary
    }

    with open(CAMERA_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")


def camera_monitor():
    cam = cv2.VideoCapture(CAMERA_INDEX)

    if not cam.isOpened():
        print("Camera not found")
        return

    print("Camera monitor started")

    last_summary = ""

    while True:
        ret, frame = cam.read()

        if not ret:
            print("Camera read failed")
            time.sleep(5)
            continue

        summary = analyze_camera_frame(frame)

        if summary and summary != last_summary:
            print("Camera:", summary)
            save_camera_log(summary)
            last_summary = summary

        time.sleep(CAMERA_CHECK_SECONDS)


def read_camera_logs():
    if not os.path.exists(CAMERA_LOG_FILE):
        return ""

    with open(CAMERA_LOG_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()

    return "".join(lines[-200:])


def ask_camera_memory(question):
    logs = read_camera_logs()

    if not logs:
        return "No camera logs yet."

    payload = {
        "model": MODEL,
        "prompt": f"""
You are Gmoon camera memory.

Answer using only these camera logs.
If unsure, say "I am not sure."
Do not accuse. Say "logs suggest" when needed.
Keep answer short.

Camera logs:
{logs}

Question:
{question}
""",
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        answer = response.json().get("response", "").strip()
        return answer if answer else "I am not sure."
    except Exception as e:
        print("Camera memory error:", e)
        return "Camera memory failed."


def is_camera_question(command):
    words = [
        "camera",
        "what did he do",
        "what he did",
        "from morning",
        "from mrng",
        "did he",
        "did she",
        "who cleaned",
        "clean vessels",
        "wash vessels",
        "washed vessels",
        "did he smoke",
        "did he cook",
        "person came",
        "when did",
        "what time"
    ]

    return any(word in command.lower() for word in words)


def handle_command(command):
    command = command.lower().strip()

    if is_camera_question(command):
        return ask_camera_memory(command)

    if command in ["open chrome", "start chrome"]:
        subprocess.Popen("chrome")
        return "Opening Chrome"

    if command in ["open notepad", "start notepad"]:
        subprocess.Popen("notepad")
        return "Opening Notepad"

    if command in ["open calculator", "start calculator"]:
        subprocess.Popen("calc")
        return "Opening Calculator"

    if command in ["open file explorer", "open files"]:
        subprocess.Popen("explorer")
        return "Opening Files"

    if command in ["open command prompt", "open cmd"]:
        subprocess.Popen("cmd")
        return "Opening CMD"

    if command in ["open youtube", "youtube"]:
        webbrowser.open("https://youtube.com")
        return "Opening YouTube"

    if command in ["open google", "google"]:
        webbrowser.open("https://google.com")
        return "Opening Google"

    if command in ["open gmail", "gmail"]:
        webbrowser.open("https://mail.google.com")
        return "Opening Gmail"

    if command in ["open github", "github"]:
        webbrowser.open("https://github.com")
        return "Opening GitHub"

    if command.startswith("search "):
        query = command.replace("search ", "", 1)
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return "Searching Google"

    if command.startswith("play "):
        song = command.replace("play ", "", 1)
        webbrowser.open(f"https://www.youtube.com/results?search_query={song}")
        return "Searching YouTube"

    if "time" in command:
        now = datetime.now().strftime("%I:%M %p")
        return f"It is {now}"

    if "date" in command:
        today = datetime.now().strftime("%d %B %Y")
        return f"Today is {today}"

    if command.startswith("remember "):
        note = command.replace("remember ", "", 1)
        with open("notes.txt", "a", encoding="utf-8") as file:
            file.write(note + "\n")
        return "I remembered it"

    if command in ["read notes", "show notes", "what did i remember"]:
        try:
            with open("notes.txt", "r", encoding="utf-8") as file:
                notes = file.read().strip()
            return notes if notes else "No notes saved"
        except FileNotFoundError:
            return "No notes saved"

    if command in ["clear notes", "delete notes"]:
        open("notes.txt", "w", encoding="utf-8").close()
        return "Notes cleared"

    if command in ["shutdown pc", "turn off pc"]:
        os.system("shutdown /s /t 5")
        return "Shutting down PC"

    if command in ["restart pc", "reboot pc"]:
        os.system("shutdown /r /t 5")
        return "Restarting PC"

    if command in ["lock pc", "lock computer"]:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Locking PC"

    return None


def ask_gmoon(prompt):
    live_words = ["news", "latest", "today", "weather", "current", "live"]
    use_google = any(word in prompt.lower() for word in live_words)

    live_info = google_search(prompt) if use_google else ""

    payload = {
        "model": MODEL,
        "prompt": f"""
You are Gmoon.

Rules:
- reply under 8 words
- be natural
- no explanation

User:
{prompt}

Search results:
{live_info}
""",
        "stream": False
    }

    start = time.time()

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        answer = response.json().get("response", "").strip()

        if not answer:
            answer = "I have no answer."

    except Exception as e:
        print("Ollama error:", e)
        answer = "Brain connection failed."

    elapsed = round(time.time() - start, 2)
    return answer, elapsed


def listen():
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.2)

        audio = recognizer.listen(
            source,
            timeout=5,
            phrase_time_limit=5
        )

    return recognizer.recognize_google(audio)


if CAMERA_ENABLED:
    camera_thread = threading.Thread(target=camera_monitor, daemon=True)
    camera_thread.start()


print("===================================")
print("        GMOON AI READY")
print("===================================")

speak("Gmoon online")

while True:
    try:
        print("\nWaiting for wake word...")

        text = listen().lower()
        print("Heard:", text)

        if WAKE_WORD not in text:
            continue

        print("Wake word detected!")
        speak("Yes?")

        print("Listening for command...")
        user_text = listen()

        print("You:", user_text)

        command = user_text.lower().strip()

        if command in ["exit", "stop", "quit", "shutdown"]:
            speak("Shutting down")
            break

        local_answer = handle_command(command)

        if local_answer:
            answer = local_answer
            response_time = 0
        else:
            answer, response_time = ask_gmoon(user_text)

        print("Gmoon:", answer)
        print("Response Time:", response_time, "sec")

        save_chat(user_text, answer)
        speak(answer)

    except sr.WaitTimeoutError:
        print("Listening timeout")

    except sr.UnknownValueError:
        print("Could not understand")

    except KeyboardInterrupt:
        print("\nStopped by user")
        speak("Shutting down")
        break

    except Exception as e:
        print("Error:", e)
        speak("Error occurred")