from django.contrib.auth import get_user_model
from django.db import transaction
from ninja import Router

from notification.models import Notification, NotificationEmail, NotificationSMS
from notification.schemas import ErrorOut, NotificationScheduleIn
from notification.schemas import NotificationScheduleOut

router = Router()


@router.get("/")
def list_notifications(request):
    """List notifications, each with a single status (see CHALLENGE.md, Task 3)."""
    return []


@router.post("/")
def update_notifications(request):
    """Ingest a lifecycle state report or a list of them (see CHALLENGE.md, Task 2).

    Report shape: see ``samples/state_reports.json``.
    """
    return []


@router.post(
    "/schedule-send",
    response={201: NotificationScheduleOut, 404: ErrorOut},
)
def schedule_send(request, payload: NotificationScheduleIn):
    User = get_user_model()
    try:
        user = User.objects.get(username=payload.user)
    except User.DoesNotExist:
        return 404, {"detail": f"User '{payload.user}' does not exist."}

    with transaction.atomic():
        notification = Notification.objects.create(
            user=user,
            deliver_at=payload.deliver_at,
        )

        if payload.channels.email is not None:
            NotificationEmail.objects.create(
                notification=notification,
                to=payload.channels.email.to,
                title=payload.channels.email.title,
                body=payload.channels.email.body,
            )

        if payload.channels.sms is not None:
            NotificationSMS.objects.create(
                notification=notification,
                to=payload.channels.sms.to,
                text=payload.channels.sms.text,
            )

    channels = {}
    if payload.channels.email is not None:
        channels["email"] = payload.channels.email
    if payload.channels.sms is not None:
        channels["sms"] = payload.channels.sms

    return 201, {
        "id": notification.id,
        "user": user.username,
        "deliver_at": notification.deliver_at,
        "channels": channels,
    }
