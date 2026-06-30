from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from redis import Redis
from redis.exceptions import ResponseError

from config.redis_client import get_redis_client
from notification.models import (
    EmailStatus,
    NotificationEmail,
    NotificationSMS,
    SMSStatus,
)
from notification.schemas import StateReportIn

EMAIL_TRACKING_PREFIX = "em_"
SMS_TRACKING_PREFIX = "sm_"


@dataclass(frozen=True)
class QueuedStateReport:
    tracking_id: str
    status: str
    occurred_at: datetime
    received_at: datetime

    @property
    def ordering_key(self) -> tuple[datetime, datetime]:
        return self.occurred_at, self.received_at


def enqueue_state_report(
    report: StateReportIn,
    client: Redis | None = None,
) -> None:
    enqueue_state_reports([report], client=client)


def enqueue_state_reports(
    reports: Iterable[StateReportIn],
    client: Redis | None = None,
) -> None:
    redis_client = client if client is not None else get_redis_client()
    stream = settings.NOTIFICATION_STATE_REPORT_STREAM
    pipeline = redis_client.pipeline(transaction=False)

    for report in reports:
        pipeline.xadd(stream, state_report_fields(report))

    pipeline.execute()


def state_report_fields(report: StateReportIn) -> dict[str, str]:
    return {
        "tracking_id": report.tracking_id,
        "status": report.status,
        "occurred_at": report.occurred_at.isoformat(),
        "received_at": report.received_at.isoformat(),
    }


def consume_state_report_batch(
    *,
    client: Redis | None = None,
    consumer: str | None = None,
    batch_size: int | None = None,
    max_wait_seconds: float | None = None,
) -> dict[str, int]:
    redis_client = client if client is not None else get_redis_client()
    stream = settings.NOTIFICATION_STATE_REPORT_STREAM
    group = settings.NOTIFICATION_STATE_REPORT_GROUP
    consumer_name = consumer or settings.NOTIFICATION_STATE_REPORT_CONSUMER
    batch_limit = batch_size or settings.NOTIFICATION_STATE_REPORT_BATCH_SIZE
    max_wait = (
        settings.NOTIFICATION_STATE_REPORT_MAX_WAIT_SECONDS
        if max_wait_seconds is None
        else max_wait_seconds
    )

    ensure_consumer_group(redis_client, stream, group)
    entries = read_batch(
        redis_client,
        stream=stream,
        group=group,
        consumer=consumer_name,
        batch_size=batch_limit,
        max_wait_seconds=max_wait,
    )
    if not entries:
        return {
            "read": 0,
            "invalid": 0,
            "email_reports": 0,
            "sms_reports": 0,
            "email_rows_updated": 0,
            "sms_rows_updated": 0,
            "deleted": 0,
        }

    email_reports, sms_reports, invalid_count = categorize_reports(entries)

    with transaction.atomic():
        email_rows_updated = bulk_update_channel(
            NotificationEmail,
            email_reports.values(),
        )
        sms_rows_updated = bulk_update_channel(
            NotificationSMS,
            sms_reports.values(),
        )

    delete_entries(redis_client, stream, group, [entry_id for entry_id, _ in entries])

    return {
        "read": len(entries),
        "invalid": invalid_count,
        "email_reports": len(email_reports),
        "sms_reports": len(sms_reports),
        "email_rows_updated": email_rows_updated,
        "sms_rows_updated": sms_rows_updated,
        "deleted": len(entries),
    }


def ensure_consumer_group(client: Redis, stream: str, group: str) -> None:
    try:
        client.xgroup_create(stream, group, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def read_batch(
    client: Redis,
    *,
    stream: str,
    group: str,
    consumer: str,
    batch_size: int,
    max_wait_seconds: float,
) -> list[tuple[str, dict[str, str]]]:
    entries = read_pending(client, stream, group, consumer, batch_size)
    deadline = time.monotonic() + max_wait_seconds

    while len(entries) < batch_size:
        remaining_seconds = deadline - time.monotonic()
        if entries and remaining_seconds <= 0:
            break

        block_ms = max(1, int(max(remaining_seconds, 0) * 1000))
        response = client.xreadgroup(
            group,
            consumer,
            {stream: ">"},
            count=batch_size - len(entries),
            block=block_ms,
        )
        if not response:
            break

        for _, stream_entries in response:
            entries.extend(stream_entries)

    return entries


def read_pending(
    client: Redis,
    stream: str,
    group: str,
    consumer: str,
    batch_size: int,
) -> list[tuple[str, dict[str, str]]]:
    response = client.xreadgroup(
        group,
        consumer,
        {stream: "0"},
        count=batch_size,
    )
    if not response:
        return []

    entries: list[tuple[str, dict[str, str]]] = []
    for _, stream_entries in response:
        entries.extend(stream_entries)
    return entries


def categorize_reports(
    entries: Iterable[tuple[str, dict[str, str]]],
) -> tuple[dict[str, QueuedStateReport], dict[str, QueuedStateReport], int]:
    email_statuses = set(EmailStatus.values)
    sms_statuses = set(SMSStatus.values)
    email_reports: dict[str, QueuedStateReport] = {}
    sms_reports: dict[str, QueuedStateReport] = {}
    invalid_count = 0

    for _, fields in entries:
        report = parse_report(fields)
        if report is None:
            invalid_count += 1
            continue

        if report.tracking_id.startswith(EMAIL_TRACKING_PREFIX):
            if report.status not in email_statuses:
                invalid_count += 1
                continue
            keep_latest(email_reports, report)
        elif report.tracking_id.startswith(SMS_TRACKING_PREFIX):
            if report.status not in sms_statuses:
                invalid_count += 1
                continue
            keep_latest(sms_reports, report)
        else:
            invalid_count += 1

    return email_reports, sms_reports, invalid_count


def parse_report(fields: dict[str, str]) -> QueuedStateReport | None:
    try:
        occurred_at = parse_stream_datetime(fields["occurred_at"])
        received_at = parse_stream_datetime(fields["received_at"])
        tracking_id = fields["tracking_id"]
        status = fields["status"]
    except (KeyError, ValueError, TypeError):
        return None

    if not tracking_id or not status:
        return None

    return QueuedStateReport(
        tracking_id=tracking_id,
        status=status,
        occurred_at=occurred_at,
        received_at=received_at,
    )


def parse_stream_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def keep_latest(
    reports: dict[str, QueuedStateReport],
    report: QueuedStateReport,
) -> None:
    current = reports.get(report.tracking_id)
    if current is None or report.ordering_key >= current.ordering_key:
        reports[report.tracking_id] = report


def bulk_update_channel(
    model: type[NotificationEmail] | type[NotificationSMS],
    reports: Iterable[QueuedStateReport],
) -> int:
    report_list = list(reports)
    if not report_list:
        return 0

    table_name = connection.ops.quote_name(model._meta.db_table)
    value_placeholders = ", ".join(
        ["(%s::varchar, %s::varchar, %s::timestamptz, %s::timestamptz)"]
        * len(report_list)
    )
    sql = f"""
        UPDATE {table_name} AS target
        SET
            status = data.status,
            occurred_at = data.occurred_at,
            received_at = data.received_at,
            updated_at = %s
        FROM (VALUES {value_placeholders})
            AS data(tracking_id, status, occurred_at, received_at)
        WHERE target.tracking_id = data.tracking_id
          AND (
              target.occurred_at IS NULL
              OR target.occurred_at < data.occurred_at
              OR (
                  target.occurred_at = data.occurred_at
                  AND (
                      target.received_at IS NULL
                      OR target.received_at <= data.received_at
                  )
              )
          )
    """

    params: list[object] = [timezone.now()]
    for report in report_list:
        params.extend(
            [
                report.tracking_id,
                report.status,
                report.occurred_at,
                report.received_at,
            ]
        )

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount


def delete_entries(
    client: Redis, stream: str, group: str, entry_ids: list[str]
) -> None:
    if not entry_ids:
        return

    pipeline = client.pipeline(transaction=False)
    pipeline.xack(stream, group, *entry_ids)
    pipeline.xdel(stream, *entry_ids)
    pipeline.execute()
