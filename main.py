import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")

# FastAPI app definition
app = FastAPI(
    title="GPT Todoist Integration",
    version="1.0.0",
    description="A simple API to allow a GPT to add tasks to a user's Todoist account"
)

# === Utilities ===

def get_next_friday():
    today = datetime.now()
    days_ahead = 4 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

# === Request Body Model ===

class TaskRequest(BaseModel):
    content: str  # title of the task
    task_description: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[List[str]] = None

# === Endpoint ===

@app.post("/add_task")
async def add_task(request: TaskRequest):
    # Prepare task data
    payload = {
        "content": request.content,
        "description": request.task_description or "",
        "due_date": request.due_date or get_next_friday(),
        "labels": request.labels or [],
        "priority": 3
    }

    # Call Todoist API
    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://api.todoist.com/rest/v2/tasks", json=payload, headers=headers)
    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {
        "message": "Task created successfully",
        "todoist_response": response.json() if response.content else None
    }