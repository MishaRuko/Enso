"""Supabase client and CRUD helpers for all tables."""

import uuid
from datetime import UTC, datetime

from supabase import Client, create_client

from .config import SUPABASE_ANON_KEY, SUPABASE_URL

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


# ---------------------------------------------------------------------------
# design_sessions
# ---------------------------------------------------------------------------

def create_session(*, client_name: str | None = None, client_email: str | None = None) -> dict:
    row = {
        "id": uuid.uuid4().hex[:16],
        "status": "pending",
        "preferences": {},
        "furniture_list": [],
    }
    if client_name:
        row["client_name"] = client_name
    if client_email:
        row["client_email"] = client_email
    return get_client().table("design_sessions").insert(row).execute().data[0]


def get_session(session_id: str) -> dict | None:
    rows = get_client().table("design_sessions").select("*").eq("id", session_id).execute().data
    return rows[0] if rows else None


def list_sessions() -> list[dict]:
    return get_client().table("design_sessions").select("*").order("created_at", desc=True).execute().data


def update_session(session_id: str, updates: dict) -> dict:
    updates["updated_at"] = datetime.now(UTC).isoformat()
    return get_client().table("design_sessions").update(updates).eq("id", session_id).execute().data[0]


# ---------------------------------------------------------------------------
# design_jobs
# ---------------------------------------------------------------------------

def create_job(session_id: str, phase: str) -> dict:
    row = {
        "id": uuid.uuid4().hex[:16],
        "session_id": session_id,
        "status": "pending",
        "phase": phase,
        "trace": [],
    }
    return get_client().table("design_jobs").insert(row).execute().data[0]


def get_job(job_id: str) -> dict | None:
    rows = get_client().table("design_jobs").select("*").eq("id", job_id).execute().data
    return rows[0] if rows else None


def list_jobs(session_id: str) -> list[dict]:
    return (
        get_client()
        .table("design_jobs")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


def update_job(job_id: str, updates: dict) -> dict:
    return get_client().table("design_jobs").update(updates).eq("id", job_id).execute().data[0]


# ---------------------------------------------------------------------------
# furniture_items
# ---------------------------------------------------------------------------

def upsert_furniture(item: dict) -> dict:
    return get_client().table("furniture_items").upsert(item).execute().data[0]


def list_furniture(session_id: str, *, selected_only: bool = False) -> list[dict]:
    q = get_client().table("furniture_items").select("*").eq("session_id", session_id)
    if selected_only:
        q = q.eq("selected", True)
    return q.execute().data


def update_furniture(item_id: str, updates: dict) -> dict:
    return get_client().table("furniture_items").update(updates).eq("id", item_id).execute().data[0]


# ---------------------------------------------------------------------------
# models_3d
# ---------------------------------------------------------------------------

def create_model(furniture_item_id: str, source: str, *, glb_url: str = "", glb_storage_path: str = "", generation_cost: float = 0) -> dict:
    row = {
        "id": uuid.uuid4().hex[:16],
        "furniture_item_id": furniture_item_id,
        "source": source,
        "glb_url": glb_url,
        "glb_storage_path": glb_storage_path,
        "generation_cost": generation_cost,
    }
    return get_client().table("models_3d").insert(row).execute().data[0]


def get_model(model_id: str) -> dict | None:
    rows = get_client().table("models_3d").select("*").eq("id", model_id).execute().data
    return rows[0] if rows else None


def list_models(furniture_item_id: str) -> list[dict]:
    return get_client().table("models_3d").select("*").eq("furniture_item_id", furniture_item_id).execute().data


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def upload_to_storage(bucket: str, path: str, data: bytes, content_type: str = "image/png") -> str:
    client = get_client()
    client.storage.from_(bucket).upload(path, data, file_options={"content-type": content_type})
    return client.storage.from_(bucket).get_public_url(path)
