from mongoengine import Document, StringField, DateTimeField
from datetime import datetime, UTC

class Teacher(Document):
    google_id = StringField(required=True, unique=True)
    email = StringField(required=True, unique=True)
    name = StringField(required=True)
    profile_picture = StringField()
    created_at = DateTimeField(default=datetime.now(UTC))
    last_login = DateTimeField(default=datetime.now(UTC))

    meta = {
        'indexes': [
            {'fields': ['google_id'], 'unique': True},
            {'fields': ['email'], 'unique': True}
        ]
    }