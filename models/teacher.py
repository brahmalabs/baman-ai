from mongoengine import Document, StringField, DateTimeField, ReferenceField, ListField, EmbeddedDocumentField, EmbeddedDocument
from datetime import datetime, timezone
from models.channel import Channel

class Channels(EmbeddedDocument):
    telegram = ListField(ReferenceField(Channel, required=False))
    whatsapp = ListField(ReferenceField(Channel, required=False))
    facebook = ListField(ReferenceField(Channel, required=False))
    instagram = ListField(ReferenceField(Channel, required=False))

class Teacher(Document):
    google_id = StringField(required=True, unique=True)
    email = StringField(required=True, unique=True)
    name = StringField(required=True)
    profile_picture = StringField()
    channels = EmbeddedDocumentField(Channels, default=Channels)
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    last_login = DateTimeField(default=datetime.now(timezone.utc))

    meta = {
        'indexes': [
            {'fields': ['google_id'], 'unique': True},
            {'fields': ['email'], 'unique': True}
        ]
    }