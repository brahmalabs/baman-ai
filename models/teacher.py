from mongoengine import Document, StringField, DateTimeField
import datetime

class Teacher(Document):
    google_id = StringField(required=True, unique=True)
    email = StringField(required=True, unique=True)
    name = StringField(required=True)
    profile_picture = StringField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    last_login = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        'indexes': [
            {'fields': ['google_id'], 'unique': True},
            {'fields': ['email'], 'unique': True}
        ]
    }