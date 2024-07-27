import enum
from sqlalchemy import (
    Column, 
    Integer, 
    ForeignKey, 
    DateTime, 
    Enum, 
    Text
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base

class RoleType(enum.Enum):
    user = "user"
    bot = "assistant"

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'))
    role = Column(Enum('user', 'assistant', name='role_enum'))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    chat_sessions = relationship("ChatSession", back_populates="chat_messages")