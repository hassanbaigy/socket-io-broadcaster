"""Database models for the chat server."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

Base = declarative_base()

class ConversationType(str, enum.Enum):
    GROUP = "group"
    PRIVATE = "private"

class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"

class Conversation(Base):
    """Conversation model matching Laravel's conversations table."""
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    type = Column(Enum(ConversationType.GROUP, ConversationType.PRIVATE), nullable=False)
    name = Column(String(255), nullable=True)
    tenant_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    participants = relationship("ConversationParticipant", back_populates="conversation", lazy="joined")

class ConversationParticipant(Base):
    """Participant model matching Laravel's conversation_participants table."""
    __tablename__ = 'conversation_participants'

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    student_id = Column(Integer, nullable=True)
    instructor_id = Column(Integer, nullable=True)
    joined_at = Column(DateTime, nullable=True)
    left_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    messages = relationship("Message", back_populates="participant", lazy="joined")

class Message(Base):
    """Message model matching Laravel's messages table."""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    participant_id = Column(Integer, ForeignKey('conversation_participants.id'), nullable=False)
    content = Column(Text, nullable=False)
    attachment_url = Column(String(255), nullable=True)
    type = Column(Enum(MessageType.TEXT, MessageType.IMAGE, MessageType.VIDEO, MessageType.AUDIO), 
                  default=MessageType.TEXT, nullable=False)
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    participant = relationship("ConversationParticipant", back_populates="messages")

class ActiveConnection(Base):
    """Model to track active socket connections."""
    __tablename__ = 'active_connections'

    id = Column(Integer, primary_key=True)
    socket_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(Integer, nullable=False)
    is_student = Column(Integer, default=1)  # 1 for student, 0 for instructor
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_typing = Column(Integer, default=0)
    typing_in_conversation = Column(Integer, nullable=True) 