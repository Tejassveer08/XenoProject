import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from sqlalchemy import text

from app.config import settings
from app.database import async_session
from app.routers import auth, files, upload_sessions, validation_jobs

app = FastAPI(
    title="Xeno Transaction Validation Platform",
    description="Scalable transaction data validation and processing API",
    version="1.0.0",
)

# =========================
# Diagnostic Routes
# =========================

@app.get("/hello")
async def hello():
    return {"message": "deployment works"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/test-db")
async def test_db():
    return {
        "database_url": settings.database_url
    }

@app.get("/test-bcrypt")
async def test_bcrypt():
    try:
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd.hash("test123")

        return {
            "ok": True,
            "hash": hashed[:20]
        }

    except Exception as e:
        return {
            "error": str(e)
        }

@app.get("/db-ping")
async def db_ping():
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))

            return {
                "ok": result.scalar()
            }

    except Exception as e:
        return {
            "error": str(e)
        }

# =========================
# CORS
# =========================

origins = [o.strip() for o in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Routers
# =========================

app.include_router(auth.router, prefix="/api/v1")
app.include_router(upload_sessions.router, prefix="/api/v1")
app.include_router(validation_jobs.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")

# =========================
# Rule Sets
# =========================

rules_router = APIRouter(prefix="/rule-sets", tags=["rule-sets"])

@rules_router.get("")
async def list_rule_sets():
    rules_dir = Path("/app/shared/rules")

    if not rules_dir.exists():
        rules_dir = Path(__file__).resolve().parents[2] / "shared" / "rules"

    sets = []

    if rules_dir.exists():
        for f in sorted(rules_dir.glob("*.json")):
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)

            sets.append(
                {
                    "id": f.stem,
                    "name": data.get("name", f.stem),
                    "description": data.get("description", ""),
                    "dataset_types": data.get("dataset_types", []),
                }
            )

    return sets

@rules_router.get("/{rule_set_id}")
async def get_rule_set(rule_set_id: str):
    rules_dir = Path("/app/shared/rules")

    if not rules_dir.exists():
        rules_dir = Path(__file__).resolve().parents[2] / "shared" / "rules"

    path = rules_dir / f"{rule_set_id}.json"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Rule set not found"
        )

    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

app.include_router(rules_router, prefix="/api/v1")
