from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from bson.objectid import ObjectId

from db import weather_collection
from utils import replace_mongo_id

load_dotenv()

# OpenWeatherMap API Key
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

app = FastAPI(title="Weather Journal API")

# ---------- MODELS ----------
class JournalEntry(BaseModel):
    city: str
    user_note: str


# ---------- ENDPOINTS ----------

@app.get("/", tags=["Home"])
def home():
    return {"message": "Welcome to the Weather Journal API 🌦️"}


# Fetch live weather for a city and save
@app.get("/weather/{city}", tags=["Weather"])
def get_weather(city: str):
    if not OPENWEATHER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing OpenWeather API key. Please check your .env file."
        )

    # Call OpenWeatherMap API
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error connecting to OpenWeather API: {e}"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City '{city}' not found in OpenWeather API"
        )

    data = response.json()

    # Prepare weather document
    weather_data = {
        "city": city,
        "temperature": data["main"]["temp"],
        "description": data["weather"][0]["description"],
        "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "user_note": ""  # placeholder
    }

    try:
        weather_collection.insert_one(weather_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving to MongoDB: {e}"
        )

    return {"message": "Weather fetched and saved!", "data": weather_data}


# Add a user note with today's weather
@app.post("/journal", tags=["Journal"])
def add_journal(entry: JournalEntry):
    # Fetch live weather for city
    params = {"q": entry.city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="City not found")

    data = response.json()
    weather_data = {
        "city": entry.city,
        "temperature": data["main"]["temp"],
        "description": data["weather"][0]["description"],
        "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "user_note": entry.user_note
    }

    weather_collection.insert_one(weather_data)

    return {"message": "Journal entry added!", "data": weather_data}


# List all saved weather notes
@app.get("/journal", tags=["Journal"])
def list_journal():
    entries = list(weather_collection.find())
    return {"data": [replace_mongo_id(e) for e in entries]}


# Extra: Show weather trends (avg temp per city)
@app.get("/trends", tags=["Trends"])
def weather_trends():
    pipeline = [
        {"$group": {"_id": "$city", "avg_temp": {"$avg": "$temperature"}}}
    ]
    results = list(weather_collection.aggregate(pipeline))

    trends = [{"city": r["_id"], "average_temperature": round(r["avg_temp"], 2)} for r in results]
    return {"trends": trends}
