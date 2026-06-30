from celery import Task, shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from notification.models import Notification, NotificationEmail, NotificationSMS
from notification.providers import send_email as provider_send_email
from notification.providers import send_sms as provider_send_sms


class BaseNotificationTask(Task):
    abstract = True
    autoretry_for = (Exception,)
    max_retries = 5
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True
    acks_late = True
    reject_on_worker_lost = True
    ignore_result = True


@shared_task(bind=True, base=BaseNotificationTask)
def enqueue_due_notifications(self):
    now = timezone.now()
    batch_size = settings.NOTIFICATION_ENQUEUE_BATCH_SIZE

    with transaction.atomic():
        notifications = list(
            Notification.objects.select_for_update(of=("self",), skip_locked=True)
            .select_related("email", "sms")
            .filter(deliver_at__lte=now, enqueued_at__isnull=True)
            .order_by("deliver_at", "id")[:batch_size]
        )
        if not notifications:
            return {"notifications": 0, "emails": 0, "sms": 0}

        notification_ids = [notification.id for notification in notifications]
        email_ids = []
        sms_ids = []

        for notification in notifications:
            email = getattr(notification, "email", None)
            if email is not None and email.tracking_id is None:
                email_ids.append(email.id)

            sms = getattr(notification, "sms", None)
            if sms is not None and sms.tracking_id is None:
                sms_ids.append(sms.id)

        for email_id in email_ids:
            send_email.delay(email_id)

        for sms_id in sms_ids:
            send_sms.delay(sms_id)

        Notification.objects.filter(id__in=notification_ids).update(
            enqueued_at=now,
            updated_at=now,
        )

    return {
        "notifications": len(notification_ids),
        "emails": len(email_ids),
        "sms": len(sms_ids),
    }


@shared_task(bind=True, base=BaseNotificationTask)
def send_email(self, email_id):
    with transaction.atomic():
        email = (
            NotificationEmail.objects.select_for_update(skip_locked=True)
            .filter(id=email_id, tracking_id__isnull=True)
            .first()
        )
        if email is None:
            return None

        tracking_id = provider_send_email(email.to, email.title, email.body)
        email.tracking_id = tracking_id
        email.save(update_fields=["tracking_id", "updated_at"])

    return tracking_id


@shared_task(bind=True, base=BaseNotificationTask)
def send_sms(self, sms_id):
    with transaction.atomic():
        sms = (
            NotificationSMS.objects.select_for_update(skip_locked=True)
            .filter(id=sms_id, tracking_id__isnull=True)
            .first()
        )
        if sms is None:
            return None

        tracking_id = provider_send_sms(sms.to, sms.text)
        sms.tracking_id = tracking_id
        sms.save(update_fields=["tracking_id", "updated_at"])

    return tracking_id
