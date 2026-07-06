import uuid

from django.db import models


class TimeStampedUUIDModel(models.Model):
    """Abstract base: UUID primary key + created/updated timestamps.

    UUID PKs avoid enumerable IDs on public marketplace resources.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
