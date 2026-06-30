# Implementation Notes

## Modeling

`Notification` stays as the logical message owned by one user and scheduled for one `deliver_at`. Email and SMS are separate one-to-one channel models because their payload fields, provider tracking ids, and lifecycle states differ. This keeps channel-specific rules close to the channel while still letting one notification contain email, SMS, or both.

Simple model schema:

| Model | Main fields | Relation |
| --- | --- | --- |
| `Notification` | `user`, `deliver_at`, `enqueued_at` | Parent logical notification |
| `NotificationEmail` | `to`, `title`, `body`, `tracking_id`, `status`, `occurred_at`, `received_at` | One-to-one with `Notification` |
| `NotificationSMS` | `to`, `text`, `tracking_id`, `status`, `occurred_at`, `received_at` | One-to-one with `Notification` |

## State Reports

The API validates the report shape, required timestamps, and allowed status strings before accepting work. Accepted reports are appended to a Redis stream instead of being applied in the request path, so `POST /api/notifications/` can stay fast under bursts. The consumer drains batches, separates email and SMS reports by tracking-id prefix, rejects statuses that are invalid for that channel, keeps only the newest report per tracking id in the batch, and performs bulk PostgreSQL updates guarded by timestamp ordering.

The first validation is handled by the request schema. It rejects missing `tracking_id`, `status`, `occurred_at`, or `received_at`; invalid datetime format; wrong field type; empty `tracking_id`; or empty `status`. After that, the consumer validates that `tracking_id` starts with a known prefix: `em_` for email or `sm_` for SMS.

## Aggregated Status

The read endpoint returns the individual channel statuses plus one notification-level status. This was a weird part of the challenge and hard to decide, because one logical notification can have two channels in different states. I chose to summarize by the clearest user-facing signal:

| Channel statuses | Single status |
| --- | --- |
| No channel status yet | `pending` |
| Any channel is `opened` | `opened` |
| Any channel is `delivered` | `delivered` |
| Any channel is `bounced`, `failed`, or `undelivered` | `failed` |
| Any channel is `sent` | `sent` |
| Fallback | `pending` |

This means a multi-channel notification can still show success if one channel clearly reached the user, while still surfacing total lack of progress as pending.

## Load And Scaling

The ingestion path is intentionally queue-first: API processes only validate and enqueue, while consumers batch database writes. At higher scale I would use Kafka instead of Redis for this stream, but I skipped it here because Kafka setup would add too much operational weight for this challenge. I would also run multiple web and consumer replicas and move provider callbacks behind authentication/signature verification.
