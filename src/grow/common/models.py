from __future__ import annotations

import uuid
from typing import Any

from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AppendOnlyModel(models.Model):
    """Application-level immutability; database permissions remain a deployment concern."""

    objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk and self.__class__.objects.filter(pk=self.pk).exists():
            raise ValueError(f"{self.__class__.__name__} records are append-only")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValueError(f"{self.__class__.__name__} records are append-only")
