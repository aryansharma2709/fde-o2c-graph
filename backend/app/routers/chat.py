"""Chat router for natural language queries."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/")
def chat(request: Dict[str, Any]) -> Dict[str, Any]:
    """Process a natural language chat query.
    
    Expected request body:
    {
        "prompt": "Which products have the highest billing document count?"
    }
    """
    try:
        prompt = request.get("prompt", "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required and must not be empty")

        service = ChatService()
        response = service.chat(prompt)

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")
