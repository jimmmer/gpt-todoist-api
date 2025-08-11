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

# === AI compile + static page ===
import os
from typing import Dict, Any
from fastapi import Body
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# OpenAI SDK (Responses API with structured outputs)
# Docs: https://platform.openai.com/docs/api-reference/chat/create  https://openai.com/index/introducing-structured-outputs-in-the-api/
# --- OpenAI setup (replace your existing OpenAI bits with this) ---
from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ai_client = OpenAI(api_key=OPENAI_API_KEY)

TASK_SCHEMA = {
    "name": "TaskPayload",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "content":    {"type": "string",  "description": "Task title"},
            "description":{"type": "string",  "description": "Markdown body"},
            "due_date":   {"type": "string",  "description": "YYYY-MM-DD; default to next Friday if missing"},
            "labels":     {"type": "array",   "items": {"type": "string"}},
            "priority":   {"type": "integer", "minimum": 1, "maximum": 4}
        },
        "required": ["content", "description"]  # only the truly required fields
    }
}

def format_instructions_for_model(xml_snippet: str) -> str:
    return f"""
You convert JIRA XML to a Todoist task JSON payload.

Rules:
- Extract title from <summary> into 'content'.
- Build a markdown 'description' with this layout (keep links clickable):
  **JIRA Ticket**: [KEY](https://atyponjira.atlassian.net/browse/KEY)
  **Reporter**: ...
  **Assignee**: ...
  **Created**: ...
  **Updated**: ...

  **Related Tickets**:
  - [KEY](https://atyponjira.atlassian.net/browse/KEY)
  - [KEY](https://atyponjira.atlassian.net/browse/KEY)

  ---
  **Summary**
  (short paragraph)

  ---
  **Comments Summary**
  - bullet points

  ---
  **Action Required**
  (one sentence)

- Labels: prefer existing labels (respect capitalization):
  Urgent, 2024-MR6, 2024-MR7, 2024-MR8, PB Configs, CR, Improvement, Inquiry,
  Bug, Task, Discovery, Implementation, QA/Testing, RFR, Waiting On Feedback,
  E-Reader, Analytics, Help, Reminder, Internal.
- Priority mapping: P1→priority 4 (+ label 'Urgent' if appropriate), P2→3, P3→2, default→1.
- Type/status/component: map to existing labels when possible (Bug, Task, Implementation,
  Waiting On Feedback, Internal, Analytics, E-Reader). Create a new label only if no close match exists.
- Fixed Version: if like "lit-2410-tandf-6.0":
    1) If a '2024-MR6' label exists, use that.
    2) Else use '2410 MR6'. Remove lowercase prefixes/words and dashes.
- due_date: use YYYY-MM-DD; if missing, set to next Friday.
- Output MUST match the JSON schema exactly.

JIRA XML:
{xml_snippet}
""".strip()

def compile_task_payload_from_xml(xml_text: str) -> dict:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured.")

    # Use Chat Completions with structured outputs
    resp = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a careful API that returns strictly valid JSON."},
            {"role": "user", "content": format_instructions_for_model(xml_text)}
        ],
        response_format={ "type": "json_schema", "json_schema": TASK_SCHEMA },
        temperature=0
    )

    payload_text = resp.choices[0].message.content or ""
    try:
        data = json.loads(payload_text)
    except Exception:
        raise HTTPException(status_code=502, detail="AI returned invalid JSON payload.")

    if not data.get("due_date"):
        data["due_date"] = get_next_friday()
    data["labels"] = data.get("labels") or []
    p = data.get("priority")
    if p is None or not isinstance(p, int) or p < 1 or p > 4:
        data["priority"] = 1
    return data

@app.post("/compile_task_from_xml")
def compile_task_from_xml(body: Dict[str, str] = Body(...)):
    """
    Accepts: { "xml": "<issue>...</issue>" }
    Returns: { content, description, due_date, labels, priority }
    """
    xml_text = (body or {}).get("xml", "")
    if not xml_text.strip():
        raise HTTPException(status_code=400, detail="Missing 'xml' in request body.")
    return compile_task_payload_from_xml(xml_text)

@app.post("/create_task_from_xml")
def create_task_from_xml(body: Dict[str, Any] = Body(...)):
    """
    Accepts:
      { "xml": "<issue>...</issue>" }                    # create new
      { "xml": "<issue>...</issue>", "task_id": "123" }  # update existing
    """
    xml_text = (body or {}).get("xml", "")
    if not xml_text.strip():
        raise HTTPException(status_code=400, detail="Missing 'xml' in request body.")

    task_id = (body or {}).get("task_id")
    compiled = compile_task_payload_from_xml(xml_text)

    headers = {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Content-Type": "application/json"
    }
    if not TODOIST_API_TOKEN:
        raise HTTPException(status_code=500, detail="TODOIST_API_TOKEN not configured.")

    if task_id:
        # Update existing
        resp = requests.post(
            f"https://api.todoist.com/rest/v2/tasks/{task_id}",
            headers=headers,
            json={
                "content": compiled["content"],
                "description": compiled["description"],
                "due_date": compiled["due_date"],
                "labels": compiled["labels"],
                "priority": compiled["priority"],
            },
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return {"message": "Task updated successfully", "task_id": task_id}
    else:
        # Create new
        resp = requests.post(
            "https://api.todoist.com/rest/v2/tasks",
            headers=headers,
            json=compiled,
        )
        if resp.status_code not in (200, 204):
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return {"message": "Task created successfully", "todoist_response": resp.json() if resp.content else None}

# Serve a simple frontend from / (index.html in ./static)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))