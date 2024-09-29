"""Database models for students"""

from datetime import datetime, timezone
from uuid import uuid4

from mongoengine import (
    Document,
    StringField,
    DateTimeField,
    ListField,
    ReferenceField
)


class Student(Document):
    """Student details along with their social network IDs and contact details"""

    id = StringField(default=lambda: str(uuid4()), primary_key=True)
    name = StringField(required=True)
    email = StringField(unique=True, sparse=True)
    phone_number = StringField(unique=True, sparse=True)
    profile_picture = StringField()
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    last_login = DateTimeField(default=datetime.now(timezone.utc))

    # Extra fields for student
    bio = StringField()
    interests = ListField(StringField())
    school = StringField()
    grade = StringField()
    allowed_assistants = ListField(ReferenceField('Assistant'))

    # Social profile IDs
    google_id = StringField(unique=True, sparse=True)
    whatsapp_id = StringField(unique=True, sparse=True)
    telegram_id = StringField(unique=True, sparse=True)
    instagram_id = StringField(unique=True, sparse=True)

    # Social contact IDs
    wa_number = StringField()
    tg_handle = StringField()
    ig_handle = StringField()
    fb_handle = StringField()

    meta = {
        'indexes': [
            {'fields': ['google_id']},
            {'fields': ['whatsapp_id']},
            {'fields': ['telegram_id']},
            {'fields': ['instagram_id']},
            {'fields': ['email']},
            {'fields': ['phone_number']}
        ]
    }

    def update_last_login(self):
        """Update last login time for student"""

        self.last_login = datetime.now(timezone.utc)
        self.save()
