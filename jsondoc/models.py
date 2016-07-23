import uuid

from django.db import models
from django.contrib.postgres.fields import JSONField


class Document(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = JSONField()

    class Meta:
        abstract = True


class DatedDocument(Document):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
