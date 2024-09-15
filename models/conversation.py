from mongoengine import Document, ReferenceField, StringField, ListField, FloatField, EmbeddedDocument, EmbeddedDocumentField, EmbeddedDocumentListField, UUIDField, GenericEmbeddedDocumentField
from models.student import Student
from models.assistant import Assistant
import uuid

class Reference(EmbeddedDocument):
    pinecone_id = StringField(required=True)
    match_score = FloatField(required=True)

class References(EmbeddedDocument):
    title_matches = EmbeddedDocumentListField(Reference)
    topic_matches = EmbeddedDocumentListField(Reference)
    keyword_matches = EmbeddedDocumentListField(Reference)
    content_matches = EmbeddedDocumentListField(Reference)

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
    content = GenericEmbeddedDocumentField(choices=[UserMessage, AssistantMessage])  # Updated line

class Conversation(Document):
    uuid = UUIDField(required=True, default=uuid.uuid4, unique=True)
    student = ReferenceField(Student, required=True)
    assistant = ReferenceField(Assistant, required=True)
    conversation_summary = StringField()
    topics = ListField(StringField())
    title = StringField()
    keywords = ListField(StringField())
    questions = ListField(StringField())
    messages = EmbeddedDocumentListField(Message)

    meta = {'collection': 'conversations'}