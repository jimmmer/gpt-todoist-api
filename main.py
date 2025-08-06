import os
import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

API_KEY = os.getenv("MY_PRIVATE_API_KEY")
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")

class AddTaskRequest(BaseModel):
    task_name: str
    due_date: str = None

@app.post("/add_task")
async def add_task(req: AddTaskRequest, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    response = requests.post(
        "https://api.todoist.com/rest/v2/tasks",
        headers={
            "Authorization": f"Bearer {TODOIST_API_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "content": req.task_name,
            "due_string": req.due_date
        }
    )
    return response.json()