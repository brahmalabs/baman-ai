from mongoengine import Document, ReferenceField, StringField, ListField, EmbeddedDocument, EmbeddedDocumentListField, DateTimeField
from models.teacher import Teacher
import uuid
from datetime import datetime, UTC


class DigestedContent(EmbeddedDocument):
    id = StringField(default=lambda: str(uuid.uuid4()), primary_key=True)
    content = StringField(required=True)
    title = StringField(required=False)
    topics = ListField(StringField())
    keywords = ListField(StringField())
    short_summary = StringField()
    long_summary = StringField()
    questions = ListField(StringField())

class Content(EmbeddedDocument):
    id = StringField(default=lambda: str(uuid.uuid4()), primary_key=True)
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
    id = StringField(default=lambda: str(uuid.uuid4()), primary_key=True)
    teacher = ReferenceField(Teacher, required=True)
    subject = StringField(required=True)
    class_name = StringField(required=True)
    about = StringField(required=False)
    profile_picture = StringField(required=False)
    own_content = EmbeddedDocumentListField(Content)
    supporting_content = EmbeddedDocumentListField(Content)
    allowed_students = ListField(ReferenceField('Student'))
    created_at = DateTimeField(default=datetime.now(UTC))
    updated_at = DateTimeField(default=datetime.now(UTC))

    meta = {
        'indexes': [
            {'fields': ['teacher', 'subject', 'class_name']}
        ]
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(UTC)
        return super(Assistant, self).save(*args, **kwargs)
    
