import os
import sys

import django
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pensieve.settings")
load_dotenv()
django.setup()

from chatbot.services.ingest import ingest_documents  # noqa: E402

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found in environment.")
        sys.exit(1)
    print(ingest_documents())
