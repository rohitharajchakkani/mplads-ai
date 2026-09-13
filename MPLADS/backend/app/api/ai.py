"""Protected read-only Ask AI endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.assistant import ask
from app.api.deps import IntelligencePrincipal, get_db, require_intelligence_principal
from app.schemas.ai import AskAiRequest, AskAiResponse

router = APIRouter(dependencies=[Depends(require_intelligence_principal)])

@router.post("/ai/ask", response_model=AskAiResponse)
def ask_ai(payload: AskAiRequest, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    try: return ask(payload.question, payload.context, principal, db)
    except ValueError as exc: raise HTTPException(429 if "limit" in str(exc) else 422, detail={"code": "AI_REQUEST_REJECTED", "message": str(exc)}) from exc
