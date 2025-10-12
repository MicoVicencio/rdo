# run_all.py
import threading
from app import app  # replace with your Flask app file name
from main import Repo  # replace with your Tkinter GUI file name

def run_flask():
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)

# Start Flask in background
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Start Tkinter GUI
if __name__ == "__main__":
    Repo()
