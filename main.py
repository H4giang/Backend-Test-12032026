from fastapi import FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from bson import ObjectId
from datetime import datetime
import json
import asyncio
from typing import List, Optional

# Import models từ file models.py của bạn
from .models import TaskCreate, TaskResponse


app = FastAPI(title="Task Management System - Advanced API")

# --- KẾT NỐI DATABASE & REDIS --- [cite: 43, 52]
client = AsyncIOMotorClient("mongodb://mongodb:27017")
db = client.task_db
rd = redis.from_url("redis://redis:6379", decode_responses=True)

# --- WORKER XỬ LÝ ACTIVITY LOG (EVENT-DRIVEN) --- [cite: 156, 162, 164]
async def activity_log_worker():
    pubsub = rd.pubsub()
    await pubsub.subscribe("activity_events")
    async for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            # Lưu vết vào MongoDB [cite: 203, 204]
            await db.activity_logs.insert_one({
                **data,
                "timestamp": datetime.utcnow()
            })

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(activity_log_worker())

# --- HELPER: VALIDATE OBJECTID --- [cite: 166, 173]
def validate_id(id_str: str):
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail=f"ID '{id_str}' không đúng định dạng 24 ký tự hex.")
    return ObjectId(id_str)

# --- API ENDPOINTS ---

@app.post("/tasks", response_model=TaskResponse, status_code=201, tags=["Tasks"]) # [cite: 82, 111]
async def create_task(task: TaskCreate):
    # Validate IDs 
    proj_id = validate_id(task.project_id)
    assignee_id = validate_id(task.assignee_id)

    task_dict = task.dict()
    task_dict.update({
        "project_id": proj_id,
        "assignee_id": assignee_id,
        "created_at": datetime.utcnow(),
        "comments": [] # Embedded comments [cite: 59, 140]
    })

    # MongoDB: Insert [cite: 55]
    result = await db.tasks.insert_one(task_dict)
    task_id_str = str(result.inserted_id)

    # Pub/Sub: Gửi sự kiện tạo task [cite: 157, 160]
    await rd.publish("activity_events", json.dumps({
        "action": "CREATE",
        "entity_type": "TASK",
        "entity_id": task_id_str,
        "details": f"Task '{task.title}' created"
    }))

    return {**task_dict, "id": task_id_str}

@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"]) # [cite: 79, 112]
async def get_task(task_id: str):
    oid = validate_id(task_id)
    
    # Redis: Cache-aside Pattern [cite: 148, 154]
    cache_key = f"task:{task_id}"
    cached = await rd.get(cache_key)
    if cached:
        return json.loads(cached)

    # MongoDB Query [cite: 53]
    task = await db.tasks.find_one({"_id": oid})
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy Task")
    
    task["id"] = str(task["_id"])
    del task["_id"]
    task["project_id"] = str(task["project_id"])
    task["assignee_id"] = str(task["assignee_id"])

    # Lưu Cache 60s [cite: 148]
    await rd.setex(cache_key, 60, json.dumps(task, default=str))
    return task

@app.get("/tasks", tags=["Tasks"]) # [cite: 81, 113]
async def list_tasks(
    status: Optional[str] = None, 
    limit: int = Query(10, le=100), 
    skip: int = 0
):
    # Filtering & Pagination [cite: 76, 120, 121]
    query = {}
    if status:
        query["status"] = status
    
    cursor = db.tasks.find(query).skip(skip).limit(limit).sort("created_at", -1) # Sorting 
    tasks = await cursor.to_list(length=limit)
    
    for t in tasks:
        t["id"] = str(t["_id"])
        t["project_id"] = str(t["project_id"])
        t["assignee_id"] = str(t["assignee_id"])
        del t["_id"]
    return tasks

@app.get("/logs", tags=["Logs"]) # [cite: 203]
async def get_logs(limit: int = 20):
    cursor = db.activity_logs.find().sort("timestamp", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    for l in logs:
        l["id"] = str(l["_id"])
        del l["_id"]
    return logs

@app.get("/tasks/stats", tags=["Advanced"]) # [cite: 127, 128]
async def get_task_stats():
    # MongoDB Aggregation Pipeline [cite: 126, 142]
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    cursor = db.tasks.aggregate(pipeline)
    return await cursor.to_list(length=100)


    