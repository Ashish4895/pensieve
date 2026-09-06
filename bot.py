from asyncio import futures
import os
import sys
import sqlite3
from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()


# Quick check to ensure the environment variable is loaded
if not os.environ.get("GEMINI_API_KEY"):
    print("Error: GEMINI_API_KEY environment variable not set.")
    print("Please run: export GEMINI_API_KEY='your_key' (or set on Windows)")
    sys.exit(1)


# Database Helper Functions
def init_db(db_path="chat_history.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )
    conn.commit()
    return conn


def load_history(conn, session_id="default"):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    )
    rows = cursor.fetchall()

    history = []
    for role, content in rows:
        history.append(
            types.Content(role=role, parts=[types.Part.from_text(text=content)])
        )
    return history


def save_message(conn, session_id, role, content):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.commit()


# Session configuration
SESSION_ID = "default"

# Initialize DB connection
conn = init_db()

# Load previous chat history
db_history = load_history(conn, SESSION_ID)

# Initialize the GenAI client
client = genai.Client()

# Start a chat session using the standard gemini-2.5-flash model and loaded history
chat = client.chats.create(model="gemini-2.5-flash", history=db_history)

print("===============================================")
print(" AI Chatbot Initialized! Type 'quit' to exit.")
if db_history:
    print(f" Loaded {len(db_history)} previous message turns from history.")
print("===============================================\n")

try:
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() == "quit":
                print("Goodbye!")
                break

            if not user_input.strip():
                continue

            # Save user message to database
            save_message(conn, SESSION_ID, "user", user_input)

            # Send message to the model; history is tracked automatically by the SDK during this session
            response = chat.send_message(user_input)
            print(f"\nAI: {response.text}\n")

            # Save AI response to database
            save_message(conn, SESSION_ID, "model", response.text)

        except Exception as e:
            print(f"\nAn error occurred: {e}\n")
finally:
    conn.close()
