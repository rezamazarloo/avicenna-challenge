from __future__ import annotations

from datetime import datetime

from ninja import Schema
from pydantic import Field, model_validator


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
