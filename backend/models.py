from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    JSON,
    DateTime,
    Boolean,
    Enum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List as ListType
import enum

Base = declarative_base()


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class BoardRole(enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class Priority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    owned_boards = relationship(
        "Board", back_populates="owner", cascade="all, delete-orphan"
    )
    board_memberships = relationship(
        "BoardMember", back_populates="user", cascade="all, delete-orphan"
    )
    sent_invitations = relationship(
        "Invitation", foreign_keys="Invitation.inviter_id", back_populates="inviter"
    )
    received_invitations = relationship(
        "Invitation", foreign_keys="Invitation.invitee_id", back_populates="invitee"
    )
    card_contributions = relationship(
        "CardContributor", back_populates="user", cascade="all, delete-orphan"
    )


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign key to user (owner)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="owned_boards")
    members = relationship(
        "BoardMember", back_populates="board", cascade="all, delete-orphan"
    )
    lists = relationship(
        "TaskList", back_populates="board", cascade="all, delete-orphan"
    )
    invitations = relationship(
        "Invitation", back_populates="board", cascade="all, delete-orphan"
    )


class BoardMember(Base):
    __tablename__ = "board_members"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(BoardRole), default=BoardRole.MEMBER)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    board = relationship("Board", back_populates="members")
    user = relationship("User", back_populates="board_memberships")


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)
    inviter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invitee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    # Relationships
    board = relationship("Board", back_populates="invitations")
    inviter = relationship(
        "User", foreign_keys=[inviter_id], back_populates="sent_invitations"
    )
    invitee = relationship(
        "User", foreign_keys=[invitee_id], back_populates="received_invitations"
    )


class TaskList(Base):
    __tablename__ = "task_lists"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)

    # Relationships
    board = relationship("Board", back_populates="lists")
    cards = relationship(
        "Card", back_populates="task_list", cascade="all, delete-orphan"
    )


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, default=0)
    checklist = Column(JSON, default=list)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    list_id = Column(Integer, ForeignKey("task_lists.id"), nullable=False)

    # Relationships
    task_list = relationship("TaskList", back_populates="cards")
    creator = relationship("User", foreign_keys=[created_by])
    contributors = relationship(
        "CardContributor", back_populates="card", cascade="all, delete-orphan"
    )


class CardContributor(Base):
    __tablename__ = "card_contributors"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contributed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    card = relationship("Card", back_populates="contributors")
    user = relationship("User", back_populates="card_contributions")
