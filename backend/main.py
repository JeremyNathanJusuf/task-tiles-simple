from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import timedelta
import json
import os

# Import database components
from database import get_db, init_database
from models import User as UserModel, Board as BoardModel, TaskList as TaskListModel, Card as CardModel
from auth import (
    authenticate_user, 
    create_access_token, 
    get_current_active_user, 
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Task Tiles API", description="A multi-user Kanban-style task management API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True


class BoardCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ListCreate(BaseModel):
    title: str
    board_id: int


class CardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    list_id: int


class Card(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    list_id: int
    position: int = 0
    checklist: List[str] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TaskList(BaseModel):
    id: int
    title: str
    position: int = 0
    cards: List[Card] = []
    created_at: str

    class Config:
        from_attributes = True


class Board(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    lists: List[TaskList] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MoveCard(BaseModel):
    new_list_id: int
    new_position: int


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when the application starts"""
    init_database()


@app.get("/")
async def root():
    return {"message": "Task Tiles API is running with multi-user support!"}


# Authentication endpoints
@app.post("/api/register", response_model=User)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    if db.query(UserModel).filter(UserModel.username == user_data.username).first():
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    if db.query(UserModel).filter(UserModel.email == user_data.email).first():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = UserModel(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@app.post("/api/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token"""
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


# Board endpoints
@app.get("/api/boards", response_model=List[Board])
async def get_boards(current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get all boards for the current user"""
    boards = db.query(BoardModel).filter(BoardModel.owner_id == current_user.id).all()
    
    board_list = []
    for board in boards:
        # Get lists for this board
        lists = db.query(TaskListModel).filter(TaskListModel.board_id == board.id).order_by(TaskListModel.position).all()
        
        board_data = {
            "id": board.id,
            "title": board.title,
            "description": board.description,
            "created_at": board.created_at.isoformat(),
            "updated_at": board.updated_at.isoformat(),
            "lists": []
        }
        
        for task_list in lists:
            # Get cards for this list
            cards = db.query(CardModel).filter(CardModel.list_id == task_list.id).order_by(CardModel.position).all()
            
            list_data = {
                "id": task_list.id,
                "title": task_list.title,
                "position": task_list.position,
                "created_at": task_list.created_at.isoformat(),
                "cards": [
                    {
                        "id": card.id,
                        "title": card.title,
                        "description": card.description,
                        "list_id": card.list_id,
                        "position": card.position,
                        "checklist": card.checklist or [],
                        "created_at": card.created_at.isoformat(),
                        "updated_at": card.updated_at.isoformat()
                    }
                    for card in cards
                ]
            }
            board_data["lists"].append(list_data)
        
        board_list.append(board_data)
    
    return board_list


@app.post("/api/boards", response_model=Board)
async def create_board(board_data: BoardCreate, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Create a new board"""
    board = BoardModel(
        title=board_data.title,
        description=board_data.description,
        owner_id=current_user.id
    )
    
    db.add(board)
    db.commit()
    db.refresh(board)
    
    return {
        "id": board.id,
        "title": board.title,
        "description": board.description,
        "created_at": board.created_at.isoformat(),
        "updated_at": board.updated_at.isoformat(),
        "lists": []
    }


@app.get("/api/boards/{board_id}", response_model=Board)
async def get_board(board_id: int, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get a specific board with all its lists and cards"""
    board = db.query(BoardModel).filter(BoardModel.id == board_id, BoardModel.owner_id == current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Get lists for this board
    lists = db.query(TaskListModel).filter(TaskListModel.board_id == board.id).order_by(TaskListModel.position).all()
    
    board_data = {
        "id": board.id,
        "title": board.title,
        "description": board.description,
        "created_at": board.created_at.isoformat(),
        "updated_at": board.updated_at.isoformat(),
        "lists": []
    }
    
    for task_list in lists:
        # Get cards for this list
        cards = db.query(CardModel).filter(CardModel.list_id == task_list.id).order_by(CardModel.position).all()
        
        list_data = {
            "id": task_list.id,
            "title": task_list.title,
            "position": task_list.position,
            "created_at": task_list.created_at.isoformat(),
            "cards": [
                {
                    "id": card.id,
                    "title": card.title,
                    "description": card.description,
                    "list_id": card.list_id,
                    "position": card.position,
                    "checklist": card.checklist or [],
                    "created_at": card.created_at.isoformat(),
                    "updated_at": card.updated_at.isoformat()
                }
                for card in cards
            ]
        }
        board_data["lists"].append(list_data)
    
    return board_data


@app.post("/api/lists", response_model=TaskList)
async def create_list(list_data: ListCreate, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Create a new list"""
    # Verify the board exists and belongs to the user
    board = db.query(BoardModel).filter(BoardModel.id == list_data.board_id, BoardModel.owner_id == current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Calculate new position
    max_position = db.query(TaskListModel).filter(TaskListModel.board_id == list_data.board_id).count()
    
    # Create new list
    new_list = TaskListModel(
        title=list_data.title,
        position=max_position,
        board_id=list_data.board_id
    )
    
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    
    return {
        "id": new_list.id,
        "title": new_list.title,
        "position": new_list.position,
        "created_at": new_list.created_at.isoformat(),
        "cards": []
    }


@app.post("/api/cards", response_model=Card)
async def create_card(card_data: CardCreate, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Create a new card"""
    # Verify the list exists and belongs to the user
    task_list = db.query(TaskListModel).filter(TaskListModel.id == card_data.list_id).first()
    if not task_list:
        raise HTTPException(status_code=404, detail="List not found")
    
    # Verify the board belongs to the user
    board = db.query(BoardModel).filter(BoardModel.id == task_list.board_id, BoardModel.owner_id == current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Calculate new position (last in the list)
    max_position = db.query(CardModel).filter(CardModel.list_id == card_data.list_id).count()
    
    # Create new card
    new_card = CardModel(
        title=card_data.title,
        description=card_data.description,
        list_id=card_data.list_id,
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
        "checklist": new_card.checklist or [],
        "created_at": new_card.created_at.isoformat(),
        "updated_at": new_card.updated_at.isoformat()
    }


@app.put("/api/cards/{card_id}/move", response_model=Card)
async def move_card(card_id: int, move_data: MoveCard, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Move a card to a different list or position"""
    # Find the card and verify ownership
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Verify the user owns the board
    task_list = db.query(TaskListModel).filter(TaskListModel.id == card.list_id).first()
    board = db.query(BoardModel).filter(BoardModel.id == task_list.board_id, BoardModel.owner_id == current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Verify the target list exists and belongs to the same board
    target_list = db.query(TaskListModel).filter(TaskListModel.id == move_data.new_list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")
    
    target_board = db.query(BoardModel).filter(BoardModel.id == target_list.board_id, BoardModel.owner_id == current_user.id).first()
    if not target_board:
        raise HTTPException(status_code=404, detail="Target board not found")
    
    old_list_id = card.list_id
    old_position = card.position
    
    # Update positions of other cards
    if old_list_id != move_data.new_list_id:
        # Move cards up in the old list
        db.query(CardModel).filter(
            CardModel.list_id == old_list_id,
            CardModel.position > old_position
        ).update({"position": CardModel.position - 1})
        
        # Move cards down in the new list to make room
        db.query(CardModel).filter(
            CardModel.list_id == move_data.new_list_id,
            CardModel.position >= move_data.new_position
        ).update({"position": CardModel.position + 1})
    else:
        # Moving within the same list
        if move_data.new_position > old_position:
            # Moving down in the list
            db.query(CardModel).filter(
                CardModel.list_id == old_list_id,
                CardModel.position > old_position,
                CardModel.position <= move_data.new_position
            ).update({"position": CardModel.position - 1})
        elif move_data.new_position < old_position:
            # Moving up in the list
            db.query(CardModel).filter(
                CardModel.list_id == old_list_id,
                CardModel.position >= move_data.new_position,
                CardModel.position < old_position
            ).update({"position": CardModel.position + 1})
    
    # Update the card
    card.list_id = move_data.new_list_id
    card.position = move_data.new_position
    
    db.commit()
    db.refresh(card)
    
    return {
        "id": card.id,
        "title": card.title,
        "description": card.description,
        "list_id": card.list_id,
        "position": card.position,
        "checklist": card.checklist or [],
        "created_at": card.created_at.isoformat(),
        "updated_at": card.updated_at.isoformat()
    }


@app.delete("/api/boards/{board_id}")
async def delete_board(board_id: int, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Delete a board"""
    board = db.query(BoardModel).filter(BoardModel.id == board_id, BoardModel.owner_id == current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    db.delete(board)
    db.commit()
    
    return {"message": "Board deleted successfully"}


@app.delete("/api/lists/{list_id}")
async def delete_list(list_id: int, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Delete a list"""
    task_list = db.query(TaskListModel).filter(TaskListModel.id == list_id).first()
    if not task_list:
        raise HTTPException(status_code=404, detail="List not found")
    
    # Verify the user owns the board
    board = db.query(BoardModel).filter(BoardModel.id == task_list.board_id, BoardModel.owner_id == current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    db.delete(task_list)
    db.commit()
    
    return {"message": "List deleted successfully"}


@app.delete("/api/cards/{card_id}")
async def delete_card(card_id: int, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Delete a card"""
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Verify the user owns the board
    task_list = db.query(TaskListModel).filter(TaskListModel.id == card.list_id).first()
    board = db.query(BoardModel).filter(BoardModel.id == task_list.board_id, BoardModel.owner_id == current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    db.delete(card)
    db.commit()
    
    return {"message": "Card deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
