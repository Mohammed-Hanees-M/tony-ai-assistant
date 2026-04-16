import time
import uuid
import json
from sqlalchemy.orm import Session
from apps.backend.database.models.notification import NotificationEvent

class NotificationRepository:
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def create_notification(self, event_type: str, title: str, message: str, payload: dict = None, related_task_id: str = None, user_id: str = None) -> NotificationEvent:
        now = time.time()
        event_id = str(uuid.uuid4())
        payload_str = json.dumps(payload or {})
        
        notif = NotificationEvent(
            event_id=event_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            payload_json=payload_str,
            related_task_id=related_task_id,
            created_at=now
        )
        self.db.add(notif)
        self.db.commit()
        return notif

    def list_unread_notifications(self, user_id: str = None, include_acknowledged: bool = False):
        query = self.db.query(NotificationEvent).filter(NotificationEvent.read_at == None)
        if user_id:
            query = query.filter(NotificationEvent.user_id == user_id)
        if not include_acknowledged:
            query = query.filter(NotificationEvent.acknowledged == False)
        return query.order_by(NotificationEvent.created_at.desc()).all()

    def mark_notification_read(self, event_id: str):
        notif = self.db.query(NotificationEvent).filter(NotificationEvent.event_id == event_id).first()
        if notif:
            notif.read_at = time.time()
            self.db.commit()
            print(f"[NOTIF REPO] Marked {event_id} as READ.")
        return notif

    def acknowledge_notification(self, event_id: str):
        notif = self.db.query(NotificationEvent).filter(NotificationEvent.event_id == event_id).first()
        if notif:
            notif.acknowledged = True
            if not notif.read_at:
                notif.read_at = time.time()
            self.db.commit()
            print(f"[NOTIF REPO] Acknowledged {event_id}.")
        return notif
