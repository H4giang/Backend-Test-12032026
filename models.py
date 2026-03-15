from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class Comment(BaseModel):
    user_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskCreate(BaseModel):
    title: str
    description: str
    project_id: str
    assignee_id: str
    status: str = "todo" # [cite: 123]

class TaskResponse(TaskCreate):
    id: str
    comments: List[Comment] = []
    created_at: datetime

class ActivityLogSchema(BaseModel):
    action: str  # Ví dụ: "CREATE", "UPDATE", "DELETE" [cite: 205, 206, 208]
    entity_type: str  # Ví dụ: "TASK" [cite: 109]
    entity_id: str
    user_id: str
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)