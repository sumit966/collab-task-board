# Real-Time Collaborative Task Board

Kanban-style task board where team members create, assign, and move tasks with live updates over WebSockets. Includes JWT authentication, role-based access control, and a fully typed FastAPI backend.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![WebSockets](https://img.shields.io/badge/WebSockets-010101?style=for-the-badge&logo=socket.io&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

## Overview

A production-style task board backend that demonstrates:

1. JWT authentication (register + login)
2. Role-based access control (member vs admin)
3. Boards and tasks with full CRUD
4. Real-time WebSocket broadcast on every task change
5. Per-board "rooms" so clients only receive updates for their board
6. SQLite storage with a clean relational schema
7. Type-safe request/response models with Pydantic

Every task change is broadcast to all connected clients in the same board, giving instant multi-user sync.

## Problem Statement

Teams need a shared task board that:

- Syncs instantly across multiple users (no refresh)
- Prevents unauthorized access (per-user data isolation)
- Distinguishes roles (only admins can manage certain things)
- Works without heavyweight infrastructure
- Provides a clean API for any frontend (React, Vue, mobile)

Most simple demos skip auth, roles, or real-time sync. This project includes all three.

## Solution

A FastAPI service with:

- JWT auth on every protected endpoint (Bearer token)
- WebSocket endpoint /ws/boards/{id} that broadcasts changes
- SQLite storage for users, boards, tasks
- Clean separation: auth -> storage -> events -> API
- Graceful fallback if jose/passlib aren't installed (mock hashing for dev)

## Architecture

Client (React/Vue/Mobile)
    |
    |--- HTTP (JWT Bearer) ----> FastAPI
    |                              |
    |                              v
    |                    +------------------+
    |                    |  Auth (JWT)      |
    |                    |  Storage (SQLite)|
    |                    |  Events Manager  |
    |                    +--------+---------+
    |                             |
    |--- WebSocket ----+          |
    |                  |          |
    |   /ws/boards/{id}          |
    |                  v          v
    |            Broadcast on task change
    |                             |
    +<--------------------------+

## Tech Stack

| Category | Technologies |
|----------|-------------|
| API | FastAPI, Uvicorn, Pydantic |
| Real-time | WebSockets (FastAPI native) |
| Auth | JWT (python-jose), passlib + bcrypt |
| Storage | SQLite |
| Testing | pytest, httpx, TestClient |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Language | Python 3.11+ |

## Project Structure

collab-task-board/
├── src/
│   ├── __init__.py
│   ├── auth.py             # JWT + password hashing
│   ├── storage.py          # SQLite schema + CRUD
│   └── events.py           # WebSocket connection manager
├── api/
│   ├── __init__.py
│   └── main.py             # HTTP + WebSocket endpoints
├── tests/
│   ├── __init__.py
│   └── test_api.py         # pytest tests
├── data/                    # SQLite db (git-ignored)
├── .github/workflows/ci.yml
├── Dockerfile
├── requirements.txt
├── requirements-optional.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md

## Quick Start

### 1. Clone

git clone https://github.com/sumit966/collab-task-board.git
cd collab-task-board

### 2. Virtual environment

Windows:
python -m venv venv
venv\Scripts\activate

macOS / Linux:
python3 -m venv venv
source venv/bin/activate

### 3. Install dependencies

pip install -r requirements.txt

### 4. Start the API

uvicorn api.main:app --reload

Runs at http://localhost:8000

### 5. Open Swagger

http://localhost:8000/docs

## API Usage

### POST /register

Request:
{
  "username": "sumit",
  "password": "securepass123",
  "role": "member"
}

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}

### POST /login

Same payload as register. Returns a fresh JWT.

### GET /me

Returns the current user. Requires Bearer token.

### POST /boards

Request:
{ "name": "Sprint 42" }

Response:
{ "id": 1, "name": "Sprint 42", "owner_id": 1 }

### POST /tasks

Request:
{
  "board_id": 1,
  "title": "Implement login page",
  "description": "React + JWT",
  "assignee_id": 2
}

Response: full task object.

### PATCH /tasks/{id}

Request:
{ "status": "in_progress" }

Valid statuses: todo | in_progress | review | done

### GET /boards/{id}/tasks

Returns all tasks in a board.

### WebSocket /ws/boards/{id}?token=JWT

Connect from any WebSocket client. Receives events:

{ "type": "connected", "board_id": 1 }
{ "type": "task_created", "task": {...} }
{ "type": "task_updated", "task": {...} }
{ "type": "tasks_snapshot", "tasks": [...] }

Send { "type": "refresh" } to request a full snapshot.

### Other Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| / | GET | API info |
| /health | GET | Health check |
| /me | GET | Current user |
| /users | GET | List users |
| /boards | GET | List boards |
| /docs | GET | Swagger UI |

## WebSocket Example (Python)

import asyncio
import websockets
import json

async def listen():
    url = "ws://localhost:8000/ws/boards/1?token=YOUR_JWT"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"type": "refresh"}))
        async for msg in ws:
            print(json.loads(msg))

asyncio.run(listen())

## Role-Based Access

- member: create boards, create tasks, update tasks
- admin: everything above + admin-only endpoints (extendable)

Admin check is implemented as a FastAPI dependency (require_admin) so it can be applied to any endpoint.

## WebSocket Manager Design

- manager.rooms: dict[board_id, set[WebSocket]]
- manager.broadcast(board_id, message): sends JSON to every client in the room
- Dead connections are removed automatically on send failure
- Uses asyncio.Lock to keep concurrent connect/disconnect safe

## Testing

pytest tests/ -v

Tests cover:
- Root + health
- Register and /me flow
- Unauthorized access returns 401
- Full board + task lifecycle (create board, create task, update status, list tasks)

## Docker

Build:
docker build -t collab-task-board .

Run:
docker run -p 8000:8000 collab-task-board

## CI/CD

Every push to main triggers GitHub Actions:

1. Install Python 3.11 + dependencies
2. Run pytest (uses TestClient, no live WebSocket needed)

See .github/workflows/ci.yml.

## Key Learnings

- WebSocket "rooms" per board prevent cross-board noise
- JWT works on WebSocket via query string (?token=...)
- Broadcast fan-out must handle dead connections gracefully
- FastAPI dependency injection makes role checks clean (require_admin)
- SQLite with row_factory gives dict-like rows for direct JSON responses
- TestClient supports HTTP but not WebSocket - WebSocket tests need a live server
- Graceful fallback to mock hashing keeps dev environment friction-free

## Future Improvements

- React or Vue frontend with drag-and-drop columns
- Board membership + invite system
- Task comments, attachments, activity log
- Notification emails on assignment
- MongoDB backend (already scaffolded in requirements-optional.txt)
- Rate limiting per user
- Redis pub/sub for horizontal scaling
- Deploy to GCP Cloud Run with Cloud SQL

## License

MIT License - see LICENSE file.

## Author

Sumit Raj
- M.Tech Applied AI & ML @ VNIT Nagpur
- Ex-Software Engineer Intern @ Salesforce
- GitHub: https://github.com/sumit966
- LinkedIn: https://www.linkedin.com/in/er-sumit-raj-/
- Portfolio: https://sumit966-github-io.vercel.app
- Email: info.sr0909@gmail.com

If you found this project useful, please consider giving it a star!
