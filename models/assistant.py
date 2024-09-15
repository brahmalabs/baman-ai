from mongoengine import Document, ReferenceField, StringField, ListField, EmbeddedDocument, EmbeddedDocumentListField
from models.teacher import Teacher
import uuid

class DigestedContent(EmbeddedDocument):
    content = StringField(required=True)
    title = StringField(required=False)
    topics = ListField(StringField())
    keywords = ListField(StringField())
    short_summary = StringField()
    long_summary = StringField()
    questions = ListField(StringField())

class Content(EmbeddedDocument):
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
    own_content = EmbeddedDocumentListField(Content)
    supporting_content = EmbeddedDocumentListField(Content)
    allowed_students = ListField(ReferenceField('Student'))

    meta = {
        'indexes': [
            {'fields': ['teacher', 'subject', 'class_name']}
        ]
    }
