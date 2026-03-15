from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
import os

# Cấu hình URL kết nối từ Docker Compose
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Kết nối MongoDB
client = AsyncIOMotorClient(MONGO_URL)
db = client.task_manager_db

# Kết nối Redis cho Caching/Pub-Sub
redis_client = redis.from_url(REDIS_URL, decode_responses=True)