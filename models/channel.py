from mongoengine import Document, StringField, DateTimeField, DictField, ReferenceField, ListField
from datetime import datetime, UTC
import uuid

class Channel(Document):
    id = StringField(default=lambda: str(uuid.uuid4()), primary_key=True)
    name = StringField(required=True, choices=["telegram", "whatsapp", "facebook", "instagram"])
    profile = DictField(required=True)
    teacher = ReferenceField('Teacher', required=True)
    assistants = ListField(ReferenceField('Assistant', required=False))
    created_at = DateTimeField(default=datetime.now(UTC))
    updated_at = DateTimeField(default=datetime.now(UTC))
    meta = {
        'indexes': [
          
        ]
    }