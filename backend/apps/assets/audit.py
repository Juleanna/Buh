"""Utility module for audit logging."""

import logging

from django.contrib.contenttypes.models import ContentType

from apps.assets.models import AuditLog

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract the client IP address from the request.

    Checks X-Forwarded-For first (for proxied requests),
    then falls back to REMOTE_ADDR.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(user, action, instance, changes=None, ip_address=None):
    """Create an AuditLog entry for the given action on a model instance.

    Args:
        user: The user performing the action.
        action: One of the AuditLog.Action values
                (create, update, delete, receipt, disposal,
                 depreciation, revaluation, improvement, inventory).
        instance: The model instance being acted upon.
        changes: Optional dict describing the changes made.
        ip_address: Optional client IP address string.

    Returns:
        The created AuditLog instance, or None if creation failed.
    """
    try:
        content_type = ContentType.objects.get_for_model(instance)
        return AuditLog.objects.create(
            user=user,
            action=action,
            content_type=content_type,
            object_id=instance.pk,
            object_repr=str(instance)[:500],
            changes=changes or {},
            ip_address=ip_address,
        )
    except Exception:
        logger.exception("Failed to create audit log entry")
        return None
