from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import json
import os

# Import database components
from database import get_db, init_database
from models import Board as BoardModel, TaskList as TaskListModel, Card as CardModel

app = FastAPI(title="Task Tiles API", description="A Trello-like task management API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API responses
class Card(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    list_id: int
    position: int = 0
    checklist: List[str] = []

    class Config:
        from_attributes = True


class TaskList(BaseModel):
    id: int
    title: str
    position: int = 0
    cards: List[Card] = []

    class Config:
        from_attributes = True


class Board(BaseModel):
    id: int
    title: str
    lists: List[TaskList] = []

    class Config:
        from_attributes = True


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when the application starts"""
    init_database()


@app.get("/")
async def root():
    return {"message": "Task Tiles API is running with persistent database!"}


@app.get("/api/board")
async def get_board(db: Session = Depends(get_db)):
    """Get the main board with all lists and cards"""
    # Get the first board (assuming single board for now)
    board = db.query(BoardModel).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Build the complete board structure with lists and cards
    board_data = {
        "id": board.id,
        "title": board.title,
        "lists": []
    }
    
    # Get all lists for this board, ordered by position
    lists = db.query(TaskListModel).filter(TaskListModel.board_id == board.id).order_by(TaskListModel.position).all()
    
    for task_list in lists:
        # Get all cards for this list, ordered by position
        cards = db.query(CardModel).filter(CardModel.list_id == task_list.id).order_by(CardModel.position).all()
        
        list_data = {
            "id": task_list.id,
            "title": task_list.title,
            "position": task_list.position,
            "cards": [
                {
                    "id": card.id,
                    "title": card.title,
                    "description": card.description,
                    "list_id": card.list_id,
                    "position": card.position,
                    "checklist": card.checklist or []
                }
                for card in cards
            ]
        }
        board_data["lists"].append(list_data)
    
    return board_data


@app.post("/api/lists")
async def create_list(title: str, db: Session = Depends(get_db)):
    """Create a new list"""
    # Get the first board (assuming single board for now)
    board = db.query(BoardModel).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Calculate new position
    max_position = db.query(TaskListModel).filter(TaskListModel.board_id == board.id).count()
    
    # Create new list
    new_list = TaskListModel(
        title=title,
        position=max_position,
        board_id=board.id
    )
    
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    
    return {
        "id": new_list.id,
        "title": new_list.title,
        "position": new_list.position
    }


@app.post("/api/cards")
async def create_card(title: str, description: Optional[str] = None, list_id: int = 1, db: Session = Depends(get_db)):
    """Create a new card"""
    # Verify the list exists
    task_list = db.query(TaskListModel).filter(TaskListModel.id == list_id).first()
    if not task_list:
        raise HTTPException(status_code=404, detail="List not found")
    
    # Calculate new position (last in the list)
    max_position = db.query(CardModel).filter(CardModel.list_id == list_id).count()
    
    # Create new card
    new_card = CardModel(
        title=title,
        description=description,
        list_id=list_id,
        position=max_position,
        checklist=[]
    )
    
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    
    return {
        "id": new_card.id,
        "title": new_card.title,
        "description": new_card.description,
        "list_id": new_card.list_id,
        "position": new_card.position,
        "checklist": new_card.checklist or []
    }


@app.put("/api/cards/{card_id}/move")
async def move_card(card_id: int, new_list_id: int, new_position: int, db: Session = Depends(get_db)):
    """Move a card to a different list or position"""
    # Find the card
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Verify the target list exists
    target_list = db.query(TaskListModel).filter(TaskListModel.id == new_list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")
    
    old_list_id = card.list_id
    old_position = card.position
    
    # Update positions of other cards in the old list (if moving to a different list)
    if old_list_id != new_list_id:
        # Move cards up in the old list
        db.query(CardModel).filter(
            CardModel.list_id == old_list_id,
            CardModel.position > old_position
        ).update({"position": CardModel.position - 1})
        
        # Move cards down in the new list to make room
        db.query(CardModel).filter(
            CardModel.list_id == new_list_id,
            CardModel.position >= new_position
        ).update({"position": CardModel.position + 1})
    else:
        # Moving within the same list
        if new_position > old_position:
            # Moving down in the list
            db.query(CardModel).filter(
                CardModel.list_id == old_list_id,
                CardModel.position > old_position,
                CardModel.position <= new_position
            ).update({"position": CardModel.position - 1})
        elif new_position < old_position:
            # Moving up in the list
            db.query(CardModel).filter(
                CardModel.list_id == old_list_id,
                CardModel.position >= new_position,
                CardModel.position < old_position
            ).update({"position": CardModel.position + 1})
    
    # Update the card
    card.list_id = new_list_id
    card.position = new_position
    
    db.commit()
    db.refresh(card)
    
    return {
        "id": card.id,
        "title": card.title,
        "description": card.description,
        "list_id": card.list_id,
        "position": card.position,
        "checklist": card.checklist or []
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
