from fastapi import APIRouter

router = APIRouter(prefix="/captions", tags=["captions"])


@router.get("/")
def captions_stub():
    return {"detail": "Phase 2 — not yet implemented"}
