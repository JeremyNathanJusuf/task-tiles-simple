from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from typing import List as ListType

Base = declarative_base()


class Board(Base):
    __tablename__ = "boards"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    
    # Relationship with lists
    lists = relationship("TaskList", back_populates="board", cascade="all, delete-orphan")


class TaskList(Base):
    __tablename__ = "task_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    position = Column(Integer, default=0)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=False)
    
    # Relationships
    board = relationship("Board", back_populates="lists")
    cards = relationship("Card", back_populates="task_list", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, default=0)
    checklist = Column(JSON, default=list)
    list_id = Column(Integer, ForeignKey("task_lists.id"), nullable=False)
    
    # Relationship
    task_list = relationship("TaskList", back_populates="cards") 