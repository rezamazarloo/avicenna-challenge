from django.db import models
from django.db.models import Q


class EmailStatus(models.TextChoices):
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    OPENED = "opened", "Opened"
    BOUNCED = "bounced", "Bounced"


class SMSStatus(models.TextChoices):
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"
    UNDELIVERED = "undelivered", "Undelivered"


class Notification(models.Model):
    """A single logical message to one user (see CHALLENGE.md, Task 1)."""

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    deliver_at = models.DateTimeField(
        help_text="When this notification should be delivered"
    )
    enqueued_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Set when this due notification has been queued for outbound sending."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["deliver_at"],
                name="notif_due_unqueued_idx",
                condition=Q(enqueued_at__isnull=True),
            ),
            models.Index(fields=["-created_at"], name="notif_latest_idx"),
        ]

    def __str__(self):
        return f"Notification #{self.pk} for {self.user_id}"


class NotificationEmail(models.Model):
    """Email channel payload and current lifecycle state for a notification."""

    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name="email",
    )
    to = models.EmailField()
    title = models.CharField(max_length=255)
    body = models.TextField()
    tracking_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Opaque id returned by the email provider after sending.",
    )
    status = models.CharField(
        max_length=16,
        choices=EmailStatus.choices,
        null=True,
        blank=True,
    )
    occurred_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Email for notification #{self.notification_id}"


class NotificationSMS(models.Model):
    """SMS channel payload and current lifecycle state for a notification."""

    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name="sms",
    )
    to = models.CharField(max_length=32)
    text = models.TextField()
    tracking_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Opaque id returned by the SMS provider after sending.",
    )
    status = models.CharField(
        max_length=16,
        choices=SMSStatus.choices,
        null=True,
        blank=True,
    )
    occurred_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SMS for notification #{self.notification_id}"
