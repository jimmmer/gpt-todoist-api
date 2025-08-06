from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = FastAPI()

# Load API keys from environment variables
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
API_KEY = os.getenv("MY_PRIVATE_API_KEY")


class TaskRequest(BaseModel):
    task_name: str
    due_date: str = None


class UpdateTaskRequest(BaseModel):
    task_id: str
    task_name: str = None
    due_date: str = None


@app.post("/add_task")
def add_task(task: TaskRequest, x_api_key: str = Header(...)):
    print(f"Received API key: {x_api_key}")  # 🔍 Debug line

    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "content": task.task_name
    }

    if task.due_date:
        data["due_string"] = task.due_date

    response = requests.post("https://api.todoist.com/rest/v2/tasks", headers=headers, json=data)

    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=response.status_code, detail="Failed to add task to Todoist")

    return {"message": "Task added successfully"}


@app.post("/update_task")
def update_task(task: UpdateTaskRequest, x_api_key: str = Header(...)):
    print(f"Received API key: {x_api_key}")  # 🔍 Debug line

    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {}
    if task.task_name:
        data["content"] = task.task_name
    if task.due_date:
        data["due_string"] = task.due_date

    if not data:
        raise HTTPException(status_code=400, detail="No updates provided")

    response = requests.post(
        f"https://api.todoist.com/rest/v2/tasks/{task.task_id}",
        headers=headers,
        json=data
    )

    if response.status_code != 204:
        raise HTTPException(status_code=response.status_code, detail="Failed to update task")

    return {"message": "Task updated successfully"}


@app.get("/list_tasks")
def list_tasks(x_api_key: str = Header(...)):
    print(f"Received API key: {x_api_key}")  # 🔍 Debug line

    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}"
    }

    response = requests.get("https://api.todoist.com/rest/v2/tasks", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to retrieve tasks")

    return response.json()


@app.get("/")
def root():
    return {"message": "GPT Todoist API is live"}