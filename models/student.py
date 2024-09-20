from mongoengine import Document, StringField, DateTimeField, ListField, ReferenceField
from datetime import datetime, timezone
import uuid

class Student(Document):
    id = StringField(default=lambda: str(uuid.uuid4()), primary_key=True)
    name = StringField(required=True)
    email = StringField(unique=True, sparse=True)
    phone_number = StringField(unique=True, sparse=True)
    profile_picture = StringField()
    
    google_id = StringField(unique=True, sparse=True)
    whatsapp_id = StringField(unique=True, sparse=True)
    telegram_id = StringField(unique=True, sparse=True)
    instagram_id = StringField(unique=True, sparse=True)
    
    bio = StringField()
    interests = ListField(StringField())
    school = StringField()
    grade = StringField()
    allowed_assistants = ListField(ReferenceField('Assistant'))

    wa_number = StringField()
    tg_handle = StringField()
    ig_handle = StringField()
    fb_handle = StringField()
    
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    last_login = DateTimeField(default=datetime.now(timezone.utc))

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
        self.last_login = datetime.now(timezone.utc)
        self.save()
