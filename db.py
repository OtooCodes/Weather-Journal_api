from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)

# Database & collection
weather_db = mongo_client["weather_journal_db"]
weather_collection = weather_db["weather_notes"]
