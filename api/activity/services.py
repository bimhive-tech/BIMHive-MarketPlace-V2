from activity.models import ActivityLog


def log_activity(actor, verb, target_label="", metadata=None):
    """actor may be None for system-initiated events (there are none yet, but the
    field allows for e.g. a future webhook-driven purchase)."""
    ActivityLog.objects.create(
        actor=actor,
        actor_label=getattr(actor, "email", "") or getattr(actor, "username", ""),
        verb=verb,
        target_label=target_label,
        metadata=metadata or {},
    )
