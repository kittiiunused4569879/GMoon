import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty("voices")

engine.setProperty("voice", voices[0].id)

# Faster speech
engine.setProperty("rate", 300)

# Max volume
engine.setProperty("volume", 1.0)

# Short response = faster feel
text = "System online."

engine.say(text)

engine.runAndWait()