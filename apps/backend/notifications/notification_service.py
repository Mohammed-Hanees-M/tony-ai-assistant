from sqlalchemy.orm import Session
from apps.backend.notifications.notification_repository import NotificationRepository

class NotificationService:
    def __init__(self, db_session: Session):
        self.repo = NotificationRepository(db_session)

    def _deliver(self, notif):
        print(f"[NOTIF_SERVICE] Delivery Queued: [{notif.event_type}] {notif.title} -> Task: {notif.related_task_id}")

    def notify_task_completed(self, task_id: str, goal: str, result_summary: str = ""):
        notif = self.repo.create_notification(
            event_type="task_completed",
            title=f"Task Completed: {goal[:30]}",
            message=result_summary or f"Execution of task successfully completed.",
            payload={"goal": goal},
            related_task_id=task_id
        )
        self._deliver(notif)
        return notif

    def notify_task_failed(self, task_id: str, goal: str, reason: str = ""):
        notif = self.repo.create_notification(
            event_type="task_failed",
            title=f"Task Failed: {goal[:30]}",
            message=f"Task aborted or failed fundamentally: {reason}",
            payload={"goal": goal, "reason": reason},
            related_task_id=task_id
        )
        self._deliver(notif)
        return notif

    def notify_approval_required(self, task_id: str, goal: str, risk_level: str, reason: str):
        notif = self.repo.create_notification(
            event_type="approval_required",
            title=f"Approval Required: {goal[:30]}",
            message=f"Task paused awaiting human oversight due to {risk_level} risk: {reason}",
            payload={"goal": goal, "risk_level": risk_level, "reason": reason},
            related_task_id=task_id
        )
        self._deliver(notif)
        return notif

    def notify_warning(self, title: str, message: str, task_id: str = None):
        notif = self.repo.create_notification(
            event_type="warning",
            title=f"Warning: {title}",
            message=message,
            related_task_id=task_id
        )
        self._deliver(notif)
        return notif
