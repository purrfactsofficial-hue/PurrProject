from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary_stub():
    return {"detail": "Phase 5 — not yet implemented"}
