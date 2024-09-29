"""Database models for conversation"""

from uuid import uuid4

from mongoengine import (Document,
    ReferenceField,
    StringField,
    ListField,
    FloatField,
    EmbeddedDocument,
    EmbeddedDocumentField,
    EmbeddedDocumentListField,
    GenericEmbeddedDocumentField
)

from models.student import Student
from models.assistant import Assistant


class Reference(EmbeddedDocument):
    """Represents a reference to content within the conversation."""

    content_id_digest_id = StringField(required=True)
    weighted_score = FloatField(required=True)


class References(EmbeddedDocument):
    """References related to a conversation."""

    own = EmbeddedDocumentListField(Reference)
    supporting = EmbeddedDocumentListField(Reference)


class UserMessage(EmbeddedDocument):
    """Message sent by the user during the conversation."""

    message = StringField(required=True)
    refined_question = StringField()
    topics = ListField(StringField())
    keywords = ListField(StringField())
    title = StringField()


class AssistantMessage(EmbeddedDocument):
    """Message sent by the assistant during the conversation."""

    message = StringField(required=True)
    references = EmbeddedDocumentField(References)


class Message(EmbeddedDocument):
    """Message exchanged during the conversation."""

    sender = StringField(required=True, choices=['user', 'assistant'])
    content = GenericEmbeddedDocumentField(choices=[UserMessage, AssistantMessage])


class Conversation(Document):
    """Conversation between a student and an assistant"""

    id = StringField(default=lambda: str(uuid4()), primary_key=True)
    student = ReferenceField(Student, required=True)
    assistant = ReferenceField(Assistant, required=True)
    conversation_summary = StringField()
    topics = ListField(StringField())
    title = StringField()
    keywords = ListField(StringField())
    questions = ListField(StringField())
    messages = EmbeddedDocumentListField(Message)

    # meta = {'collection': 'conversations'}
