"""app-notifier: turns events into messages in the in-app inbox (spec, Workflow 5 and Failures). The inbox is the only channel
in the MVP; Teams and e-mail would be a second subscriber, not a change here."""
from __future__ import annotations

from docai.contracts.messages import Envelope
from docai.runtime.context import Context


def _rows(env: Envelope) -> list[dict]:
    p, dept = env.payload, env.department
    snippet = p.get("text", "")
    if env.type == "hint.published":
        if p.get("reason") == "acl_change":
            return [dict(recipient_kind="user", recipient_value=p["author_oid"], title=f"Access to your note {p['hint_id']} was updated",
                         body="The dossier it rests on was restricted, so the note follows that restriction.")]
        return [dict(recipient_kind="user", recipient_value=p["author_oid"], title=f"Your hint was approved by {p.get('approved_by') or 'a steward'} and is now used in answers",
                     body=snippet, link=f"/hints/{p['hint_id']}")]
    if env.type == "hint.rejected":
        return [dict(recipient_kind="user", recipient_value=p["author_oid"], title=f"Your hint {p['hint_id']} was not accepted", body=p.get("reason", ""), link=f"/hints/{p['hint_id']}")]
    if env.type == "hint.revoked":
        return [dict(recipient_kind="user", recipient_value=p["author_oid"], title=f"Your hint {p['hint_id']} was revoked", body=p.get("reason", ""))]
    if env.type == "review.escalated":
        return [dict(recipient_kind="steward", recipient_value=dept, title=f"Review task {p.get('task_id')} needs a steward", body="It was abandoned three times.", link="/review/escalated")]
    if env.type == "dossier.failed":
        return [dict(recipient_kind="admin", recipient_value=None, title=f"Dossier {env.dossier_id} failed", body=p.get("reason", ""), link="/admin/status")]
    if env.type == "dossier.partial":
        return [dict(recipient_kind="steward", recipient_value=dept, title=f"Dossier {env.dossier_id} is searchable with gaps", body=f"{p.get('failed_pages', '?')} page(s) could not be read.", link="/review/dossiers"),
                dict(recipient_kind="admin", recipient_value=None, title=f"Dossier {env.dossier_id} ended partial", body="", link="/admin/status")]
    if env.type == "upload.rejected":
        rows = [dict(recipient_kind="admin", recipient_value=None, title=f"Upload {p.get('upload_id')} was rejected", body=p.get("reason", ""))]
        if p.get("uploaded_by"):
            rows.insert(0, dict(recipient_kind="user", recipient_value=p["uploaded_by"], title=f"Your upload {p.get('upload_id')} was rejected", body=p.get("reason", "")))
        return rows
    return []


def handle(ctx: Context, env: Envelope) -> None:
    event_id = f"{env.type}:{env.subject}:{env.created_at.isoformat()}"  # a redelivery inserts nothing twice
    for row in _rows(env):
        ctx.ops.add_inbox(type=env.type, event_id=event_id, **row)


if __name__ == "__main__":
    from docai.runtime.launch import queue_consumer

    queue_consumer(handle)
