FAILURE_STATUSES = {"bounced", "failed", "undelivered"}


def summarize_notification_status(notification):
    channels = [
        getattr(notification, "email", None),
        getattr(notification, "sms", None),
    ]
    statuses = [channel.status for channel in channels if channel is not None]

    if not statuses or all(status is None for status in statuses):
        return "pending"

    if "opened" in statuses:
        return "opened"

    if "delivered" in statuses:
        return "delivered"

    if any(status in FAILURE_STATUSES for status in statuses):
        return "failed"

    if "sent" in statuses:
        return "sent"

    return "pending"


def serialize_notification(notification):
    email = getattr(notification, "email", None)
    sms = getattr(notification, "sms", None)

    return {
        "id": notification.id,
        "user": notification.user.username,
        "deliver_at": notification.deliver_at,
        "status": summarize_notification_status(notification),
        "channels": {
            "email": serialize_channel(email) if email is not None else None,
            "sms": serialize_channel(sms) if sms is not None else None,
        },
    }


def serialize_channel(channel):
    return {"status": channel.status}
