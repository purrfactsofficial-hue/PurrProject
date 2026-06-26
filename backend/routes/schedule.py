from fastapi import APIRouter

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/queue")
def queue_stub():
    return {"items": [], "detail": "Phase 3 — not yet implemented"}
