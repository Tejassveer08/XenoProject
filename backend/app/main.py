import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, files, upload_sessions, validation_jobs

from sqlalchemy import text
from app.database import async_session

app = FastAPI(
    title="Xeno Transaction Validation Platform",
    description="Scalable transaction data validation and processing API",
    version="1.0.0",
)

@app.get("/test-db")
async def test_db():
    try:
        async with async_session() as db:
            result = await db.execute(text("SELECT 1"))
            return {"db": result.scalar()}
    except Exception as e:
        return {"error": str(e)}

# ---------------- TEST ROUTES ----------------

from passlib.context import CryptContext
from sqlalchemy import text
from app.database import async_session

@app.get("/test-bcrypt")
async def test_bcrypt():
    try:
        pwd = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto"
        )

        hashed = pwd.hash("test123")

        return {
            "ok": True,
            "hash": hashed[:20]
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/test-db")
async def test_db():
    try:
        async with async_session() as db:
            result = await db.execute(text("SELECT 1"))
            return {"db": result.scalar()}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------

origins = [o.strip() for o in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(upload_sessions.router, prefix="/api/v1")
app.include_router(validation_jobs.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")

rules_router = APIRouter(prefix="/rule-sets", tags=["rule-sets"])

# keep your existing rule-set code here unchanged

app.include_router(rules_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
