import enum
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.config import settings
from app.core.database import Base

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    heritage_id = Column(Integer, ForeignKey('heritages.id'))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), onupdate=func.now())
    quiz_count = Column(Integer, default=settings.QUIZ_COUNT)
    full_conversation = Column(Text)    # 전체 대화 내용 저장
    sliding_window = Column(Text)       # 슬라이딩 윈도우 내용 저장
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    users = relationship("User", back_populates="chat_sessions")
    heritages = relationship("Heritage", back_populates="chat_sessions")
    chat_messages = relationship("ChatMessage", back_populates="chat_sessions")

class SenderType(enum.Enum):
    user = "user"
    bot = "bot"

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(Integer, ForeignKey('chat_sessions.id'))
    sender = Column(Enum('user', 'bot', name='sender_enum'))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    chat_sessions = relationship("ChatSession", back_populates="chat_messages")