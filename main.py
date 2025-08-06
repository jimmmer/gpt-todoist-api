import os
import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Load API secrets
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
API_KEY = os.getenv("MY_PRIVATE_API_KEY")

# Request model for adding a task
class AddTaskRequest(BaseModel):
    task_name: str
    due_date: str = None  # Optional

# Request model for updating a task
class UpdateTaskRequest(BaseModel):
    task_id: str
    new_content: str

# Add a new task to Todoist
@app.post("/add_task")
async def add_task(req: AddTaskRequest, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    payload = {"content": req.task_name}
    if req.due_date:
        payload["due_string"] = req.due_date

    response = requests.post(
        "https://api.todoist.com/rest/v2/tasks",
        headers={
            "Authorization": f"Bearer {TODOIST_API_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    if response.status_code in [200, 204]:
        return {"message": "Task added successfully"}
    else:
        return {
            "error": "Failed to add task to Todoist",
            "status_code": response.status_code,
            "response": response.json()
        }

# Update an existing task
@app.post("/update_task")
async def update_task(req: UpdateTaskRequest, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    response = requests.post(
        f"https://api.todoist.com/rest/v2/tasks/{req.task_id}",
        headers={
            "Authorization": f"Bearer {TODOIST_API_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"content": req.new_content}
    )

    if response.status_code in [200, 204]:
        return {"message": "Task updated successfully"}
    else:
        return {
            "error": "Failed to update task",
            "status_code": response.status_code,
            "response": response.json()
        }

# List all active tasks
@app.get("/list_tasks")
async def list_tasks(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    response = requests.get(
        "https://api.todoist.com/rest/v2/tasks",
        headers={"Authorization": f"Bearer {TODOIST_API_TOKEN}"}
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {
            "error": "Failed to retrieve tasks",
            "status_code": response.status_code,
            "response": response.json()
        }