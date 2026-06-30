from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Schema
from pydantic import Field, field_validator, model_validator

StateReportStatus = Literal[
    "sent",
    "delivered",
    "opened",
    "bounced",
    "failed",
    "undelivered",
]
NotificationStatusOut = Literal[
    "pending",
    "sent",
    "delivered",
    "opened",
    "failed",
]


class EmailScheduleIn(Schema):
    to: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)


class SMSScheduleIn(Schema):
    to: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1)


class ChannelsScheduleIn(Schema):
    email: EmailScheduleIn | None = None
    sms: SMSScheduleIn | None = None

    @model_validator(mode="after")
    def require_at_least_one_channel(self) -> "ChannelsScheduleIn":
        if self.email is None and self.sms is None:
            raise ValueError("At least one channel is required.")
        return self


class NotificationScheduleIn(Schema):
    user: str = Field(min_length=1)
    deliver_at: datetime
    channels: ChannelsScheduleIn


class ErrorOut(Schema):
    detail: str


class MessageOut(Schema):
    detail: str


class StateReportIn(Schema):
    tracking_id: str = Field(min_length=1, max_length=64)
    status: StateReportStatus
    occurred_at: datetime
    received_at: datetime

    @field_validator("occurred_at", "received_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("Timestamp must include a timezone.")
        return value


class EmailScheduleOut(Schema):
    to: str
    title: str
    body: str


class SMSScheduleOut(Schema):
    to: str
    text: str


class ChannelsScheduleOut(Schema):
    email: EmailScheduleOut | None = None
    sms: SMSScheduleOut | None = None


class NotificationScheduleOut(Schema):
    id: int
    user: str
    deliver_at: datetime
    channels: ChannelsScheduleOut


class ChannelStatusOut(Schema):
    status: str | None = None


class NotificationChannelsOut(Schema):
    email: ChannelStatusOut | None = None
    sms: ChannelStatusOut | None = None


class NotificationOut(Schema):
    id: int
    user: str
    deliver_at: datetime
    status: NotificationStatusOut
    channels: NotificationChannelsOut
