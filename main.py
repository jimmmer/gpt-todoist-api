import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import requests
from dotenv import load_dotenv

load_dotenv()

TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")

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

def summarize_text(text, limit=500):
    return text.strip().replace("\n", " ").replace("  ", " ")[:limit] + "..."

def extract_labels(xml_root):
    labels = []

    # Priority
    priority_map = {"P1": "p1", "P2": "p2", "P3": "p3"}
    priority = xml_root.findtext(".//priority")
    todoist_priority = 1
    if priority and priority.strip().upper() in priority_map:
        labels.append(priority_map[priority.strip().upper()])
        todoist_priority = {"P1": 4, "P2": 3, "P3": 2}.get(priority.strip().upper(), 1)

    # Fixed Version → MR label
    fixed_version = xml_root.findtext(".//fixVersion")
    if fixed_version and "TF-" in fixed_version:
        mr = fixed_version.split("-")[-1].lower()
        labels.append(f"mr{mr}")

    # Type
    issue_type = xml_root.findtext(".//type")
    if issue_type:
        labels.append(issue_type.strip().lower())

    # Status
    status = xml_root.findtext(".//status")
    if status:
        labels.append(status.strip().lower())

    # Component
    component = xml_root.findtext(".//component")
    if component:
        labels.append(component.strip().lower())

    return list(set(labels)), todoist_priority  # remove duplicates

def build_task_description(xml_root):
    ticket_id = xml_root.findtext(".//key")
    summary = xml_root.findtext(".//summary")
    description = xml_root.findtext(".//description")
    reporter = xml_root.findtext(".//reporter")
    assignee = xml_root.findtext(".//assignee")
    created = xml_root.findtext(".//created")
    updated = xml_root.findtext(".//updated")

    # Related Issues
    related_links = xml_root.findall(".//issuelink")
    related_items = []
    client_links = []
    for link in related_links:
        key = link.findtext(".//issuekey")
        if key:
            link_url = f"https://atyponjira.atlassian.net/browse/{key}"
            if key.startswith("TFO"):
                client_links.append(f"[{key}]({link_url})")
            else:
                related_items.append(f"[{key}]({link_url})")

    # Comments
    comment_nodes = xml_root.findall(".//comment")
    comment_texts = [c.text.strip() for c in comment_nodes if c.text]
    comment_count = len(comment_texts)
    comment_summary = summarize_text(" ".join(comment_texts)) if comment_count else "No comments."

    # Ticket link
    ticket_url = f"https://atyponjira.atlassian.net/browse/{ticket_id}"

    # Build description
    description_block = f"""\
**JIRA Ticket**: [{ticket_id}]({ticket_url})  
**Summary**: {summary.strip() if summary else 'N/A'}

**Client Tickets**:  
{chr(10).join(client_links) if client_links else 'None'}

**Related Tickets**:  
{chr(10).join(related_items) if related_items else 'None'}

---

**Assignee**: {assignee or 'Unassigned'}  
**Reporter**: {reporter or 'N/A'}  
**Created**: {created or 'N/A'}  
**Updated**: {updated or 'N/A'}

---

**Description Summary**:  
{summarize_text(description or 'No description provided.')}

---

**Comment Summary** ({comment_count} comment{'s' if comment_count != 1 else ''}):  
{comment_summary}
"""
    return description_block

# === API Endpoint ===
@app.post("/add_task")
async def add_task(file: UploadFile = File(...)):
    content = await file.read()
    try:
        root = ET.fromstring(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid XML format")

    title = root.findtext(".//summary") or "Untitled Task"
    description = build_task_description(root)
    labels, todoist_priority = extract_labels(root)
    due_date = get_next_friday()

    payload = {
        "content": title,
        "description": description,
        "due_date": due_date,
        "labels": labels,
        "priority": todoist_priority
    }

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