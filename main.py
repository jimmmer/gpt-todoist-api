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

class UpdateTaskRequest(BaseModel):
    task_id: str
    content: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[List[str]] = None
    priority: Optional[int] = None

# === POST Endpoints ===

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

@app.post("/update_task")
async def update_task(req: UpdateTaskRequest):
    """Update a Todoist task's content/description/due_date/labels/priority."""
    if not TODOIST_API_TOKEN:
        raise HTTPException(status_code=500, detail="Todoist API token not configured.")

    if not req.task_id:
        raise HTTPException(status_code=400, detail="Missing task_id")

    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {}
    if req.content is not None:
        payload["content"] = req.content
    if req.description is not None:
        payload["description"] = req.description
    if req.due_date is not None:
        payload["due_date"] = req.due_date
    if req.labels is not None:
        payload["labels"] = req.labels
    if req.priority is not None:
        payload["priority"] = req.priority

    if not payload:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    resp = requests.post(
        f"https://api.todoist.com/rest/v2/tasks/{req.task_id}",
        headers=headers,
        json=payload,
    )

    # Todoist returns 204 No Content on success
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"message": "Task updated successfully", "task_id": req.task_id}

# === GET Endpoints ===

@app.get("/tasks")
async def list_tasks(project_id: Optional[str] = None,
                     label: Optional[str] = None,
                     filter: Optional[str] = None):
    """
    List Todoist tasks. Optional filters mirror Todoist API:
    - project_id: filter by project
    - label: filter by label name
    - filter: advanced Todoist filter query (e.g., "today | overdue")
    """
    if not TODOIST_API_TOKEN:
        raise HTTPException(status_code=500, detail="Todoist API token not configured.")

    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    params = {}
    if project_id:
        params["project_id"] = project_id
    if label:
        params["label"] = label
    if filter:
        params["filter"] = filter

    resp = requests.get("https://api.todoist.com/rest/v2/tasks", headers=headers, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Fetch a single Todoist task by ID."""
    if not TODOIST_API_TOKEN:
        raise HTTPException(status_code=500, detail="Todoist API token not configured.")

    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    resp = requests.get(f"https://api.todoist.com/rest/v2/tasks/{task_id}", headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()