from fastapi import FastAPI, HTTPException
from .models import TaskCreate, TaskResponse
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
import json
import asyncio

app = FastAPI()
# Hàm xử lý ghi log (Consumer) 
async def activity_log_worker():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("activity_events") # Đăng ký kênh sự kiện [cite: 156]
    
    async for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            # Lưu vào collection activity_logs trong MongoDB [cite: 47, 203]
            await db.activity_logs.insert_one({
                "action": data['action'],
                "entity_type": data['entity_type'],
                "entity_id": data['entity_id'],
                "user_id": data.get('user_id', 'system'),
                "details": data['details'],
                "timestamp": datetime.utcnow()
            })

# Chạy worker khi ứng dụng khởi tạo [cite: 187]
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(activity_log_worker())

# Ví dụ API Cập nhật Task có ghi log [cite: 114, 206]
@app.patch("/tasks/{task_id}")
async def update_task(task_id: str, updates: dict):
    # Cập nhật MongoDB [cite: 53]
    result = await db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": updates})
    
    if result.modified_count:
        # Publish sự kiện lên Redis [cite: 157, 160]
        event_data = {
            "action": "UPDATE",
            "entity_type": "TASK",
            "entity_id": task_id,
            "details": f"Updated fields: {list(updates.keys())}"
        }
        await redis_client.publish("activity_events", json.dumps(event_data))
        
        # Xóa cache cũ để đảm bảo dữ liệu mới (Cache Invalidation) [cite: 153]
        await redis_client.delete(f"task:{task_id}")
        
    return {"status": "updated"}

# Kết nối database [cite: 52]
client = AsyncIOMotorClient("mongodb://mongodb:27017")
db = client.task_db
rd = redis.from_url("redis://redis:6379", decode_responses=True)

@app.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    task_dict = task.dict()
    task_dict["created_at"] = datetime.utcnow()
    # MongoDB: Lưu trữ [cite: 55]
    result = await db.tasks.insert_one(task_dict)
    task_dict["id"] = str(result.inserted_id)
    return task_dict

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    # Redis Caching: [cite: 148]
    cache_key = f"task:{task_id}"
    cached = await rd.get(cache_key)
    if cached:
        return json.loads(cached)

    task = await db.tasks.find_one({"_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Lưu cache 60s
    await rd.setex(cache_key, 60, json.dumps(task, default=str))
    return task

@app.get("/logs", tags=["Activity Log"]) # Thêm tags để dễ nhìn trên Swagger
async def get_activity_logs(limit: int = 10):
    """
    Lấy danh sách lịch sử hoạt động (Activity Logs) mới nhất[cite: 17, 203].
    Hỗ trợ Pagination thông qua tham số limit[cite: 76, 121].
    """
    logs = await db.activity_logs.find().sort("timestamp", -1).to_list(limit)
    for log in logs:
        log["id"] = str(log["_id"])
        del log["_id"]
    return logs