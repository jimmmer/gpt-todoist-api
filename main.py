from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")

app = FastAPI(title="GPT Todoist Integration")

class TaskRequest(BaseModel):
    task_name: str
    due_date: str = None

@app.post("/add_task")
async def add_task(task: TaskRequest):
    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "content": task.task_name,
    }

    if task.due_date:
        data["due_string"] = task.due_date

    response = requests.post(
        "https://api.todoist.com/rest/v2/tasks",
        headers=headers,
        json=data
    )

    if response.status_code == 200 or response.status_code == 204:
        return {"message": "Task added successfully"}
    else:
        return JSONResponse(status_code=response.status_code, content={"detail": response.text})


@app.get("/list_tasks")
async def list_tasks():
    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.get(
        "https://api.todoist.com/rest/v2/tasks",
        headers=headers
    )

    if response.status_code == 200:
        return response.json()
    else:
        return JSONResponse(status_code=response.status_code, content={"detail": response.text})


@app.post("/update_task")
async def update_task(request: Request):
    body = await request.json()
    task_id = body.get("task_id")
    new_content = body.get("new_content")

    if not task_id or not new_content:
        return JSONResponse(status_code=400, content={"detail": "Missing task_id or new_content"})

    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "content": new_content
    }

    response = requests.post(
        f"https://api.todoist.com/rest/v2/tasks/{task_id}",
        headers=headers,
        json=data
    )

    if response.status_code == 204:
        return {"message": "Task updated successfully"}
    else:
        return JSONResponse(status_code=response.status_code, content={"detail": response.text})