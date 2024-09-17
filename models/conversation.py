from mongoengine import Document, ReferenceField, StringField, ListField, FloatField, EmbeddedDocument, EmbeddedDocumentField, EmbeddedDocumentListField, UUIDField, GenericEmbeddedDocumentField
from models.student import Student
from models.assistant import Assistant
import uuid

class Reference(EmbeddedDocument):
    content_id_digest_id = StringField(required=True)
    weighted_score = FloatField(required=True)

class References(EmbeddedDocument):
    own = EmbeddedDocumentListField(Reference)
    supporting = EmbeddedDocumentListField(Reference)

class UserMessage(EmbeddedDocument):
    message = StringField(required=True)
    refined_question = StringField()
    topics = ListField(StringField())
    keywords = ListField(StringField())
    title = StringField()

class AssistantMessage(EmbeddedDocument):
    message = StringField(required=True)
    references = EmbeddedDocumentField(References)

class Message(EmbeddedDocument):
    sender = StringField(required=True, choices=['user', 'assistant'])
    content = GenericEmbeddedDocumentField(choices=[UserMessage, AssistantMessage])

class Conversation(Document):
    id = StringField(default=lambda: str(uuid.uuid4()), primary_key=True)
    student = ReferenceField(Student, required=True)
    assistant = ReferenceField(Assistant, required=True)
    conversation_summary = StringField()
    topics = ListField(StringField())
    title = StringField()
    keywords = ListField(StringField())
    questions = ListField(StringField())
    messages = EmbeddedDocumentListField(Message)

    # meta = {'collection': 'conversations'}