"""Database models for assistants"""

from uuid import uuid4
from datetime import datetime, timezone

from mongoengine import (
    Document,
    ReferenceField,
    StringField,
    ListField,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    DateTimeField,
)

from models.teacher import Teacher


class DigestedContent(EmbeddedDocument):
    """Digested version of the content with additional metadata."""

    id = StringField(default=lambda: str(uuid4()), primary_key=True)
    content = StringField(required=True)
    title = StringField(required=False)
    topics = ListField(StringField())
    keywords = ListField(StringField())
    short_summary = StringField()
    long_summary = StringField()
    questions = ListField(StringField())


class Content(EmbeddedDocument):
    """Represents the main content for an Assistant, such as documents, articles, or media."""

    id = StringField(default=lambda: str(uuid4()), primary_key=True)
    file_type = StringField(required=True)
    content = StringField(required=True)
    fileUrl = StringField(required=False)
    title = StringField(required=False)
    topics = ListField(StringField())
    keywords = ListField(StringField())
    short_summary = StringField()
    long_summary = StringField()
    digests = EmbeddedDocumentListField(DigestedContent)


class Assistant(Document):
    """Assistant , who manages and curates content for students within a subject and class."""

    id = StringField(default=lambda: str(uuid4()), primary_key=True)
    teacher = ReferenceField(Teacher, required=True)
    subject = StringField(required=True)
    class_name = StringField(required=True)
    about = StringField(required=False)
    profile_picture = StringField(required=False)
    own_content = EmbeddedDocumentListField(Content)
    supporting_content = EmbeddedDocumentListField(Content)
    allowed_students = ListField(ReferenceField("Student"))
    connected_channels = ListField(ReferenceField("Channel"))
    created_at = DateTimeField(default=datetime.now(timezone.utc))
    updated_at = DateTimeField(default=datetime.now(timezone.utc))

    meta = {"indexes": [{"fields": ["teacher", "subject", "class_name"]}]}

    def save(self, *args, **kwargs):
        """Set updated_at time as current UTC time"""

        self.updated_at = datetime.now(timezone.utc)
        return super(Assistant, self).save(*args, **kwargs)
