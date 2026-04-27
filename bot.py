from flask import Flask
import threading
import time

app = Flask(__name__)

def run():
    print("BOT STARTED")

    while True:
        print("Running loop...")
        time.sleep(10)

@app.route("/")
def home():
    return "Bot is alive"

threading.Thread(target=run).start()
