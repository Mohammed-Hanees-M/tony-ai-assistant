from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.backend.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse
)

from apps.backend.database.session import get_db
from apps.backend.services.chat_service import process_chat_message

router = APIRouter()


@router.post("/", response_model=ChatMessageResponse)
async def chat_endpoint(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    try:
        response, conversation_id = process_chat_message(
            db=db,
            user_message=payload.message,
            conversation_id=payload.conversation_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ChatMessageResponse(
        response=response,
        conversation_id=conversation_id
    )