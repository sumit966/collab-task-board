"""FastAPI + WebSocket service for collaborative task board."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from auth import hash_password, verify_password, create_access_token, decode_token
from storage import (
    init_db, create_user, get_user_by_username, list_users,
    create_board, list_boards, create_task, update_task, get_task, list_tasks
)
from events import manager


app = FastAPI(
    title="Collaborative Task Board API",
    description="Kanban-style task board with real-time WebSocket updates, JWT auth, and role-based access",
    version="1.0.0",
)

security = HTTPBearer(auto_error=False)


# ---------- Models ----------
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field("member", pattern="^(member|admin)$")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class TaskCreate(BaseModel):
    board_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    assignee_id: Optional[int] = None


class TaskUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|review|done)$")
    assignee_id: Optional[int] = None
    title: Optional[str] = None


# ---------- Auth dependency ----------
def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = get_user_by_username(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user


# ---------- Startup ----------
@app.on_event("startup")
def startup():
    init_db()
    print("[OK] Database initialized")


# ---------- Health ----------
@app.get("/")
def root():
    return {"message": "Collaborative Task Board API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------- Auth endpoints ----------
@app.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    if get_user_by_username(req.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    create_user(req.username, hash_password(req.password), req.role)
    return TokenResponse(access_token=create_access_token(req.username, req.role))


@app.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(req.username, user["role"]))


@app.get("/me")
def me(user: Dict[str, Any] = Depends(get_current_user)):
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


@app.get("/users")
def users(user: Dict[str, Any] = Depends(get_current_user)):
    return list_users()


# ---------- Boards ----------
@app.post("/boards")
def board_create(req: BoardCreate, user: Dict[str, Any] = Depends(get_current_user)):
    bid = create_board(req.name, user["id"])
    return {"id": bid, "name": req.name, "owner_id": user["id"]}


@app.get("/boards")
def boards_list(user: Dict[str, Any] = Depends(get_current_user)):
    return list_boards()


# ---------- Tasks ----------
@app.post("/tasks")
async def task_create(req: TaskCreate, user: Dict[str, Any] = Depends(get_current_user)):
    tid = create_task(req.board_id, req.title, req.description, req.assignee_id)
    task = get_task(tid)
    await manager.broadcast(req.board_id, {"type": "task_created", "task": task})
    return task


@app.get("/boards/{board_id}/tasks")
def board_tasks(board_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    return list_tasks(board_id)


@app.patch("/tasks/{task_id}")
async def task_update(task_id: int, req: TaskUpdate, user: Dict[str, Any] = Depends(get_current_user)):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_task(
        task_id,
        status=req.status,
        assignee_id=req.assignee_id,
        title=req.title,
    )
    updated = get_task(task_id)
    await manager.broadcast(updated["board_id"], {"type": "task_updated", "task": updated})
    return updated


# ---------- WebSocket ----------
@app.websocket("/ws/boards/{board_id}")
async def ws_board(
    websocket: WebSocket,
    board_id: int,
    token: str = Query(...),
):
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    await manager.connect(board_id, websocket)
    try:
        await websocket.send_json({"type": "connected", "board_id": board_id})
        while True:
            data = await websocket.receive_json()
            # Client can broadcast a ping/heartbeat or request refresh
            if data.get("type") == "refresh":
                tasks = list_tasks(board_id)
                await websocket.send_json({"type": "tasks_snapshot", "tasks": tasks})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(board_id, websocket)
