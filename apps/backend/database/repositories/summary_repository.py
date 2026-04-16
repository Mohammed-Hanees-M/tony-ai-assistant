from sqlalchemy.orm import Session
from apps.backend.database.models.summary import ConversationSummary

def create_summary(db: Session, conversation_id: int, text: str, start_id: int, end_id: int):
    summary = ConversationSummary(
        conversation_id=conversation_id,
        summary_text=text,
        covered_message_start_id=start_id,
        covered_message_end_id=end_id
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary

def get_latest_summary(db: Session, conversation_id: int):
    return (
        db.query(ConversationSummary)
        .filter(ConversationSummary.conversation_id == conversation_id)
        .order_by(ConversationSummary.covered_message_end_id.desc())
        .first()
    )

def get_all_summaries(db: Session, conversation_id: int):
    return (
        db.query(ConversationSummary)
        .filter(ConversationSummary.conversation_id == conversation_id)
        .order_by(ConversationSummary.covered_message_end_id.asc())
        .all()
    )
