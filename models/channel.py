"""Database models for channel"""

from uuid import uuid4
from datetime import datetime, timezone

from mongoengine import (
    Document,
    StringField,
    DateTimeField,
    DictField,
    ReferenceField,
    ListField
)


class Channel(Document):
    """Channel for communication between teacher and assistants"""

    id = StringField(default=lambda: str(uuid4()), primary_key=True)
    name = StringField(required=True, choices=["telegram", "whatsapp", "facebook", "instagram"])
    profile = DictField(required=True)
    teacher = ReferenceField('Teacher', required=True)
    assistants = ListField(ReferenceField('Assistant', required=False))
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    updated_at = DateTimeField(default=datetime.now(timezone.utc))
