from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List, Optional, Union
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import json
import os
import re

import openai
from dotenv import load_dotenv

# Import database components
from database import get_db, init_database
from models import (
    User as UserModel,
    Board as BoardModel,
    TaskList as TaskListModel,
    Card as CardModel,
    BoardMember as BoardMemberModel,
    Invitation as InvitationModel,
    CardContributor as CardContributorModel,
    InvitationStatus,
    BoardRole,
)
from auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

app = FastAPI(
    title="Task Tiles API",
    description="A collaborative Kanban-style task management API",
)

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


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class BoardCreate(BaseModel):
    title: str
    description: Optional[str] = None


class BoardInvite(BaseModel):
    username: str
    message: Optional[str] = None


class InvitationResponse(BaseModel):
    accept: bool


class ListCreate(BaseModel):
    title: str
    board_id: int


class CardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    list_id: int
    priority: Optional[str] = "medium"


class CardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    checklist: Optional[List[str]] = None
    priority: Optional[str] = None


class Contributor(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    contributed_at: str

    class Config:
        from_attributes = True


class Card(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    list_id: int
    position: int = 0
    checklist: List[str] = []
    priority: str = "medium"
    created_at: str
    updated_at: str
    creator: User
    contributors: List[Contributor] = []

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
    owner: User
    members: List[User] = []
    is_shared: bool = False

    class Config:
        from_attributes = True


class Invitation(BaseModel):
    id: int
    board_id: int
    board_title: str
    inviter: User
    message: Optional[str] = None
    status: str
    created_at: str

    class Config:
        from_attributes = True


class MoveCard(BaseModel):
    new_list_id: int
    new_position: int


# Chatbot Models
class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: Optional[str] = None


class CurrentBoardContext(BaseModel):
    board_id: Optional[int] = None
    board_title: Optional[str] = None
    board_description: Optional[str] = None
    lists: Optional[List[dict]] = []  # List of {id, title, cards_count, cards: []}
    recent_cards: Optional[List[dict]] = []  # Recent cards for context
    total_cards: Optional[int] = 0
    members: Optional[List[dict]] = []  # Board members
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_shared: Optional[bool] = False


class ChatbotQuery(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    current_board_context: Optional[CurrentBoardContext] = None


class ChatbotResponse(BaseModel):
    message: str
    action: Optional[str] = None
    data: Optional[dict] = None


# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    openai_client = openai.OpenAI(api_key=api_key)
else:
    openai_client = None
    print("⚠️  Warning: OPENAI_API_KEY not set. AI features will be disabled.")
    print("   Create a .env file with your OpenAI API key to enable AI features.")

# OpenAI Function Definitions for Function Calling
CHATBOT_FUNCTIONS = [
    {
        "name": "get_user_boards",
        "description": "Get a list of all boards (workspaces) for the current user. Use this when user asks about 'my boards', 'what boards do I have', or similar. Each board contains multiple lists.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_todays_tasks",
        "description": "Get tasks/cards created today or containing 'today' in title/description. Use when user asks about today's work, daily tasks, or what's due today.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "create_board",
        "description": "Create a new board (workspace/project container). Only call this when user clearly wants to create a new board and provides a name.",
        "parameters": {
            "type": "object",
            "properties": {
                "board_name": {
                    "type": "string",
                    "description": "The name/title for the new board (e.g., 'Marketing Campaign', 'Personal Projects')",
                },
                "description": {
                    "type": "string",
                    "description": "Optional description for the board",
                },
            },
            "required": ["board_name"],
        },
    },
    {
        "name": "create_list",
        "description": "Create a new list (column) within a board. Only call this when user wants to create a list and you have enough information. If board_name is not provided, ask the user which board they want to add the list to.",
        "parameters": {
            "type": "object",
            "properties": {
                "list_name": {
                    "type": "string",
                    "description": "The name/title for the new list (e.g., 'To Do', 'In Progress', 'Done')",
                },
                "board_name": {
                    "type": "string",
                    "description": "The name of the board to add the list to. If not provided, will use the first available board, but it's better to ask the user for clarification.",
                },
            },
            "required": ["list_name"],
        },
    },
    {
        "name": "delete_list",
        "description": "Delete a list (column) and all its cards permanently. Only use when user explicitly wants to delete or remove a list.",
        "parameters": {
            "type": "object",
            "properties": {
                "list_name": {
                    "type": "string",
                    "description": "The name/title of the list to delete. Use partial matches if needed.",
                },
                "board_name": {
                    "type": "string",
                    "description": "Optional: the name of the board containing the list for disambiguation. If not provided, will use current board context.",
                },
            },
            "required": ["list_name"],
        },
    },
    {
        "name": "create_card",
        "description": "Create a new card/task within a list. Only call this when user wants to create a task and you have the task title. If list or board is unclear, ask for clarification first.",
        "parameters": {
            "type": "object",
            "properties": {
                "card_title": {
                    "type": "string",
                    "description": "The title/name for the new card/task (e.g., 'Write blog post', 'Fix login bug')",
                },
                "card_description": {
                    "type": "string",
                    "description": "Optional description for the card/task",
                },
                "list_name": {
                    "type": "string",
                    "description": "The name of the list to add the card to. If not provided, will use the first available list, but it's better to ask the user for clarification.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Priority level for the card (low, medium, high). Default is medium.",
                },
            },
            "required": ["card_title"],
        },
    },
    {
        "name": "move_card",
        "description": "Move a card/task from one list to another or change its position within a list. Use when user wants to move, relocate, or reorganize tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "card_title": {
                    "type": "string",
                    "description": "The title/name of the card to move. Use partial matches if needed.",
                },
                "target_list_name": {
                    "type": "string",
                    "description": "The name of the list to move the card to (e.g., 'In Progress', 'Done')",
                },
                "position": {
                    "type": "integer",
                    "description": "Optional position in the target list (0 = top, -1 = bottom). Default is bottom.",
                },
            },
            "required": ["card_title", "target_list_name"],
        },
    },
    {
        "name": "delete_card",
        "description": "Delete a card/task permanently. Only use when user explicitly wants to delete or remove a task.",
        "parameters": {
            "type": "object",
            "properties": {
                "card_title": {
                    "type": "string",
                    "description": "The title/name of the card to delete. Use partial matches if needed.",
                },
                "list_name": {
                    "type": "string",
                    "description": "Optional: the name of the list containing the card for disambiguation",
                },
            },
            "required": ["card_title"],
        },
    },
    {
        "name": "get_board_info",
        "description": "Get detailed information about a specific board, including its lists and cards. Use when user asks about a specific board or wants to know what's in a board.",
        "parameters": {
            "type": "object",
            "properties": {
                "board_name": {
                    "type": "string",
                    "description": "The name of the board to get information about. If not provided, will show info for the first board, but it's better to ask which board the user wants to know about.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_available_options",
        "description": "Get available boards and lists to help user make decisions. Use this when you need to show the user their options for creating tasks or getting information.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]


# Helper functions
def has_board_access(user_id: int, board_id: int, db: Session) -> bool:
    """Check if user has access to board (owner or member)"""
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board:
        return False

    if board.owner_id == user_id:
        return True

    membership = (
        db.query(BoardMemberModel)
        .filter(
            BoardMemberModel.board_id == board_id, BoardMemberModel.user_id == user_id
        )
        .first()
    )

    return membership is not None


def get_user_boards(user_id: int, db: Session):
    """Get all boards user has access to (owned + member of)"""
    # Get owned boards
    owned_boards = db.query(BoardModel).filter(BoardModel.owner_id == user_id).all()

    # Get boards user is member of
    memberships = (
        db.query(BoardMemberModel).filter(BoardMemberModel.user_id == user_id).all()
    )
    member_boards = [membership.board for membership in memberships]

    # Combine and remove duplicates
    all_boards = owned_boards + member_boards
    board_ids = set()
    unique_boards = []
    for board in all_boards:
        if board.id not in board_ids:
            unique_boards.append(board)
            board_ids.add(board.id)

    return unique_boards


def build_board_data(board: BoardModel, db: Session):
    """Build complete board data with lists, cards, and contributors"""
    # Get all members
    members = []
    member_records = (
        db.query(BoardMemberModel).filter(BoardMemberModel.board_id == board.id).all()
    )
    for member_record in member_records:
        members.append(
            {
                "id": member_record.user.id,
                "username": member_record.user.username,
                "email": member_record.user.email,
                "full_name": member_record.user.full_name,
                "avatar_url": member_record.user.avatar_url,
                "is_active": member_record.user.is_active,
            }
        )

    # Get lists for this board
    lists = (
        db.query(TaskListModel)
        .filter(TaskListModel.board_id == board.id)
        .order_by(TaskListModel.position)
        .all()
    )

    board_data = {
        "id": board.id,
        "title": board.title,
        "description": board.description,
        "created_at": board.created_at.isoformat(),
        "updated_at": board.updated_at.isoformat(),
        "owner": {
            "id": board.owner.id,
            "username": board.owner.username,
            "email": board.owner.email,
            "full_name": board.owner.full_name,
            "avatar_url": board.owner.avatar_url,
            "is_active": board.owner.is_active,
        },
        "members": members,
        "is_shared": len(members) > 0,
        "lists": [],
    }

    for task_list in lists:
        # Get cards for this list
        cards = (
            db.query(CardModel)
            .filter(CardModel.list_id == task_list.id)
            .order_by(CardModel.position)
            .all()
        )

        list_data = {
            "id": task_list.id,
            "title": task_list.title,
            "position": task_list.position,
            "created_at": task_list.created_at.isoformat(),
            "cards": [],
        }

        for card in cards:
            # Get contributors
            contributors = []
            contributor_records = (
                db.query(CardContributorModel)
                .filter(CardContributorModel.card_id == card.id)
                .all()
            )
            for contrib in contributor_records:
                contributors.append(
                    {
                        "id": contrib.user.id,
                        "username": contrib.user.username,
                        "full_name": contrib.user.full_name,
                        "avatar_url": contrib.user.avatar_url,
                        "contributed_at": contrib.contributed_at.isoformat(),
                    }
                )

            card_data = {
                "id": card.id,
                "title": card.title,
                "description": card.description,
                "list_id": card.list_id,
                "position": card.position,
                "checklist": card.checklist or [],
                "priority": card.priority.value if card.priority else "medium",
                "created_at": card.created_at.isoformat(),
                "updated_at": card.updated_at.isoformat(),
                "creator": {
                    "id": card.creator.id,
                    "username": card.creator.username,
                    "email": card.creator.email,
                    "full_name": card.creator.full_name,
                    "avatar_url": card.creator.avatar_url,
                    "is_active": card.creator.is_active,
                },
                "contributors": contributors,
            }
            list_data["cards"].append(card_data)

        board_data["lists"].append(list_data)

    return board_data


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when the application starts"""
    init_database()


@app.get("/")
async def root():
    return {"message": "Task Tiles API is running with collaborative features!"}


# Authentication endpoints
@app.post("/api/register", response_model=User)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    if db.query(UserModel).filter(UserModel.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    if db.query(UserModel).filter(UserModel.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = UserModel(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
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


@app.get("/api/me", response_model=UserProfile)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@app.put("/api/me", response_model=UserProfile)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update user profile"""
    if user_update.email and user_update.email != current_user.email:
        # Check if email is already taken
        existing_user = (
            db.query(UserModel)
            .filter(
                UserModel.email == user_update.email, UserModel.id != current_user.id
            )
            .first()
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already taken")
        current_user.email = user_update.email

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url

    db.commit()
    db.refresh(current_user)
    return current_user


@app.put("/api/me/password")
async def update_password(
    password_update: PasswordUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update user password"""
    from auth import verify_password

    if not verify_password(
        password_update.current_password, current_user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = get_password_hash(password_update.new_password)
    db.commit()

    return {"message": "Password updated successfully"}


# Board endpoints
@app.get("/api/boards", response_model=List[Board])
async def get_boards(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all boards user has access to"""
    boards = get_user_boards(current_user.id, db)

    board_list = []
    for board in boards:
        board_data = build_board_data(board, db)
        board_list.append(board_data)

    return board_list


@app.post("/api/boards", response_model=Board)
async def create_board(
    board_data: BoardCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new board"""
    board = BoardModel(
        title=board_data.title,
        description=board_data.description,
        owner_id=current_user.id,
    )

    db.add(board)
    db.commit()
    db.refresh(board)

    return build_board_data(board, db)


@app.get("/api/boards/{board_id}", response_model=Board)
async def get_board(
    board_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific board with all its lists and cards"""
    if not has_board_access(current_user.id, board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")

    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    return build_board_data(board, db)


@app.post("/api/boards/{board_id}/invite")
async def invite_user_to_board(
    board_id: int,
    invitation: BoardInvite,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Invite a user to collaborate on a board"""
    board = (
        db.query(BoardModel)
        .filter(BoardModel.id == board_id, BoardModel.owner_id == current_user.id)
        .first()
    )
    if not board:
        raise HTTPException(
            status_code=404, detail="Board not found or you don't have permission"
        )

    # Find the user to invite
    invitee = (
        db.query(UserModel).filter(UserModel.username == invitation.username).first()
    )
    if not invitee:
        raise HTTPException(status_code=404, detail="User not found")

    if invitee.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")

    # Check if user is already a member or has pending invitation
    existing_member = (
        db.query(BoardMemberModel)
        .filter(
            BoardMemberModel.board_id == board_id,
            BoardMemberModel.user_id == invitee.id,
        )
        .first()
    )

    if existing_member:
        raise HTTPException(
            status_code=400, detail="User is already a member of this board"
        )

    existing_invitation = (
        db.query(InvitationModel)
        .filter(
            InvitationModel.board_id == board_id,
            InvitationModel.invitee_id == invitee.id,
            InvitationModel.status == InvitationStatus.PENDING,
        )
        .first()
    )

    if existing_invitation:
        raise HTTPException(
            status_code=400, detail="User already has a pending invitation"
        )

    # Create invitation
    new_invitation = InvitationModel(
        board_id=board_id,
        inviter_id=current_user.id,
        invitee_id=invitee.id,
        message=invitation.message,
    )

    db.add(new_invitation)
    db.commit()

    return {"message": f"Invitation sent to {invitation.username}"}


@app.get("/api/invitations", response_model=List[Invitation])
async def get_user_invitations(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get pending invitations for current user"""
    invitations = (
        db.query(InvitationModel)
        .filter(
            InvitationModel.invitee_id == current_user.id,
            InvitationModel.status == InvitationStatus.PENDING,
        )
        .all()
    )

    invitation_list = []
    for invitation in invitations:
        invitation_data = {
            "id": invitation.id,
            "board_id": invitation.board_id,
            "board_title": invitation.board.title,
            "inviter": {
                "id": invitation.inviter.id,
                "username": invitation.inviter.username,
                "email": invitation.inviter.email,
                "full_name": invitation.inviter.full_name,
                "avatar_url": invitation.inviter.avatar_url,
                "is_active": invitation.inviter.is_active,
            },
            "message": invitation.message,
            "status": invitation.status.value,
            "created_at": invitation.created_at.isoformat(),
        }
        invitation_list.append(invitation_data)

    return invitation_list


@app.post("/api/invitations/{invitation_id}/respond")
async def respond_to_invitation(
    invitation_id: int,
    response: InvitationResponse,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Accept or decline a board invitation"""
    invitation = (
        db.query(InvitationModel)
        .filter(
            InvitationModel.id == invitation_id,
            InvitationModel.invitee_id == current_user.id,
            InvitationModel.status == InvitationStatus.PENDING,
        )
        .first()
    )

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if response.accept:
        # Accept invitation - add user as board member
        board_member = BoardMemberModel(
            board_id=invitation.board_id, user_id=current_user.id, role=BoardRole.MEMBER
        )
        db.add(board_member)
        invitation.status = InvitationStatus.ACCEPTED
    else:
        # Decline invitation
        invitation.status = InvitationStatus.DECLINED

    invitation.responded_at = datetime.utcnow()
    db.commit()

    action = "accepted" if response.accept else "declined"
    return {"message": f"Invitation {action} successfully"}


@app.post("/api/lists", response_model=TaskList)
async def create_list(
    list_data: ListCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new list"""
    if not has_board_access(current_user.id, list_data.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")

    # Calculate new position
    max_position = (
        db.query(TaskListModel)
        .filter(TaskListModel.board_id == list_data.board_id)
        .count()
    )

    # Create new list
    new_list = TaskListModel(
        title=list_data.title, position=max_position, board_id=list_data.board_id
    )

    db.add(new_list)
    db.commit()
    db.refresh(new_list)

    return {
        "id": new_list.id,
        "title": new_list.title,
        "position": new_list.position,
        "created_at": new_list.created_at.isoformat(),
        "cards": [],
    }


@app.post("/api/cards", response_model=Card)
async def create_card(
    card_data: CardCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new card"""
    # Verify the list exists and user has access
    task_list = (
        db.query(TaskListModel).filter(TaskListModel.id == card_data.list_id).first()
    )
    if not task_list:
        raise HTTPException(status_code=404, detail="List not found")

    if not has_board_access(current_user.id, task_list.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")

    # Calculate new position (last in the list)
    max_position = (
        db.query(CardModel).filter(CardModel.list_id == card_data.list_id).count()
    )

    # Create new card
    from models import Priority

    priority_enum = Priority.MEDIUM  # default
    if card_data.priority:
        try:
            priority_enum = Priority(card_data.priority)
        except ValueError:
            priority_enum = Priority.MEDIUM

    new_card = CardModel(
        title=card_data.title,
        description=card_data.description,
        list_id=card_data.list_id,
        position=max_position,
        created_by=current_user.id,
        checklist=[],
        priority=priority_enum,
    )

    db.add(new_card)
    db.commit()
    db.refresh(new_card)

    # Add creator as contributor
    contributor = CardContributorModel(card_id=new_card.id, user_id=current_user.id)
    db.add(contributor)
    db.commit()

    return build_card_data(new_card, db)


@app.put("/api/cards/{card_id}", response_model=Card)
async def update_card(
    card_id: int,
    card_update: CardUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a card"""
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Check board access
    task_list = db.query(TaskListModel).filter(TaskListModel.id == card.list_id).first()
    if not has_board_access(current_user.id, task_list.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")

    # Update card fields
    if card_update.title is not None:
        card.title = card_update.title
    if card_update.description is not None:
        card.description = card_update.description
    if card_update.checklist is not None:
        card.checklist = card_update.checklist
    if card_update.priority is not None:
        from models import Priority

        try:
            card.priority = Priority(card_update.priority)
        except ValueError:
            card.priority = Priority.MEDIUM

    card.updated_at = datetime.utcnow()

    # Add user as contributor if not already
    existing_contributor = (
        db.query(CardContributorModel)
        .filter(
            CardContributorModel.card_id == card_id,
            CardContributorModel.user_id == current_user.id,
        )
        .first()
    )

    if not existing_contributor:
        contributor = CardContributorModel(card_id=card_id, user_id=current_user.id)
        db.add(contributor)

    db.commit()
    db.refresh(card)

    return build_card_data(card, db)


def build_card_data(card: CardModel, db: Session):
    """Build complete card data with creator and contributors"""
    # Get contributors
    contributors = []
    contributor_records = (
        db.query(CardContributorModel)
        .filter(CardContributorModel.card_id == card.id)
        .all()
    )
    for contrib in contributor_records:
        contributors.append(
            {
                "id": contrib.user.id,
                "username": contrib.user.username,
                "full_name": contrib.user.full_name,
                "avatar_url": contrib.user.avatar_url,
                "contributed_at": contrib.contributed_at.isoformat(),
            }
        )

    return {
        "id": card.id,
        "title": card.title,
        "description": card.description,
        "list_id": card.list_id,
        "position": card.position,
        "checklist": card.checklist or [],
        "priority": card.priority.value if card.priority else "medium",
        "created_at": card.created_at.isoformat(),
        "updated_at": card.updated_at.isoformat(),
        "creator": {
            "id": card.creator.id,
            "username": card.creator.username,
            "email": card.creator.email,
            "full_name": card.creator.full_name,
            "avatar_url": card.creator.avatar_url,
            "is_active": card.creator.is_active,
        },
        "contributors": contributors,
    }


@app.put("/api/cards/{card_id}/move", response_model=Card)
async def move_card(
    card_id: int,
    move_data: MoveCard,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Move a card to a different list or position"""
    # Find the card and verify access
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Verify access to source board
    source_list = (
        db.query(TaskListModel).filter(TaskListModel.id == card.list_id).first()
    )
    if not has_board_access(current_user.id, source_list.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")

    # Verify target list exists and belongs to same board
    target_list = (
        db.query(TaskListModel)
        .filter(TaskListModel.id == move_data.new_list_id)
        .first()
    )
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    if source_list.board_id != target_list.board_id:
        raise HTTPException(
            status_code=400, detail="Cannot move cards between different boards"
        )

    old_list_id = card.list_id
    old_position = card.position

    # Update positions of other cards
    if old_list_id != move_data.new_list_id:
        # Move cards up in the old list
        db.query(CardModel).filter(
            CardModel.list_id == old_list_id, CardModel.position > old_position
        ).update({"position": CardModel.position - 1})

        # Move cards down in the new list to make room
        db.query(CardModel).filter(
            CardModel.list_id == move_data.new_list_id,
            CardModel.position >= move_data.new_position,
        ).update({"position": CardModel.position + 1})
    else:
        # Moving within the same list
        if move_data.new_position > old_position:
            # Moving down in the list
            db.query(CardModel).filter(
                CardModel.list_id == old_list_id,
                CardModel.position > old_position,
                CardModel.position <= move_data.new_position,
            ).update({"position": CardModel.position - 1})
        elif move_data.new_position < old_position:
            # Moving up in the list
            db.query(CardModel).filter(
                CardModel.list_id == old_list_id,
                CardModel.position >= move_data.new_position,
                CardModel.position < old_position,
            ).update({"position": CardModel.position + 1})

    # Update the card
    card.list_id = move_data.new_list_id
    card.position = move_data.new_position

    # Add user as contributor for moving the card
    existing_contributor = (
        db.query(CardContributorModel)
        .filter(
            CardContributorModel.card_id == card_id,
            CardContributorModel.user_id == current_user.id,
        )
        .first()
    )

    if not existing_contributor:
        contributor = CardContributorModel(card_id=card_id, user_id=current_user.id)
        db.add(contributor)

    db.commit()
    db.refresh(card)

    return build_card_data(card, db)


@app.delete("/api/boards/{board_id}")
async def delete_board(
    board_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a board (only owner can delete)"""
    board = (
        db.query(BoardModel)
        .filter(BoardModel.id == board_id, BoardModel.owner_id == current_user.id)
        .first()
    )
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    db.delete(board)
    db.commit()

    return {"message": "Board deleted successfully"}


@app.delete("/api/lists/{list_id}")
async def delete_list(
    list_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a list"""
    task_list = db.query(TaskListModel).filter(TaskListModel.id == list_id).first()
    if not task_list:
        raise HTTPException(status_code=404, detail="List not found")

    if not has_board_access(current_user.id, task_list.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")

    db.delete(task_list)
    db.commit()

    return {"message": "List deleted successfully"}


@app.delete("/api/cards/{card_id}")
async def delete_card(
    card_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a card"""
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Verify access
    task_list = db.query(TaskListModel).filter(TaskListModel.id == card.list_id).first()
    if not has_board_access(current_user.id, task_list.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")

    db.delete(card)
    db.commit()

    return {"message": "Card deleted successfully"}


@app.post("/api/chatbot", response_model=ChatbotResponse)
async def chatbot_query(
    query: ChatbotQuery,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Process chatbot queries and return intelligent responses"""
    try:
        response = await process_chatbot_query(
            query.message,
            query.conversation_history,
            query.current_board_context,
            current_user,
            db,
        )
        return response
    except Exception as e:
        return ChatbotResponse(
            message="I'm sorry, I encountered an error processing your request. Please try again.",
            action="error",
        )


async def process_chatbot_query(
    message: str,
    conversation_history: Optional[List[ChatMessage]],
    current_board_context: Optional[CurrentBoardContext],
    user: UserModel,
    db: Session,
) -> ChatbotResponse:
    """Process natural language queries using OpenAI function calling with conversation memory and current board context"""

    if not openai_client:
        return ChatbotResponse(
            message="I'm sorry, but I need an OpenAI API key to provide intelligent responses. Please contact the administrator."
        )

    try:
        # Build current board context information for the AI
        board_context_info = ""
        if current_board_context and current_board_context.board_id:
            board_context_info = f"""
CURRENT BOARD CONTEXT:
You are currently working with the "{current_board_context.board_title}" board.
Board ID: {current_board_context.board_id}
Board Description: {current_board_context.board_description or "No description"}
Board Type: {"Shared" if current_board_context.is_shared else "Personal"}
Total Cards: {current_board_context.total_cards or 0}
Members: {len(current_board_context.members or [])}
Created: {current_board_context.created_at or "Unknown"}
Last Updated: {current_board_context.updated_at or "Unknown"}

DETAILED BOARD LAYOUT:
"""
            # Add detailed list and card information
            for lst in current_board_context.lists or []:
                if isinstance(lst, dict):
                    list_title = lst.get("title", "Unknown List")
                    cards_count = lst.get("cards_count", 0)
                    board_context_info += (
                        f"\n📋 List: '{list_title}' ({cards_count} cards)\n"
                    )

                    if (
                        "cards" in lst
                        and lst["cards"]
                        and isinstance(lst["cards"], list)
                    ):
                        for i, card in enumerate(
                            lst["cards"][:10]
                        ):  # Show first 10 cards per list
                            if isinstance(card, dict):
                                card_title = card.get("title", "Unknown Card")
                                card_priority = card.get("priority", "medium")
                                card_description = card.get("description", "")
                                card_id = card.get("id", "Unknown")

                                priority_icon = (
                                    "🔴"
                                    if card_priority == "high"
                                    else "🟡" if card_priority == "medium" else "🟢"
                                )
                                board_context_info += (
                                    f"   {i+1}. {priority_icon} '{card_title}'"
                                )
                                if card_description:
                                    desc_preview = card_description[:50]
                                    if len(card_description) > 50:
                                        desc_preview += "..."
                                    board_context_info += f" - {desc_preview}"
                                board_context_info += f" (ID: {card_id})\n"

                        if cards_count > 10:
                            board_context_info += (
                                f"   ... and {cards_count - 10} more cards\n"
                            )
                    else:
                        board_context_info += "   (No cards)\n"

            if current_board_context.recent_cards:
                board_context_info += "\nRECENT ACTIVITY:\n"
                for card in current_board_context.recent_cards[:5]:  # Show last 5 cards
                    if isinstance(card, dict):
                        card_title = card.get("title", "Unknown Card")
                        list_name = card.get("list_name", "Unknown List")
                        created_at = card.get("created_at", "Unknown")
                        board_context_info += f"- '{card_title}' in '{list_name}' list (Created: {created_at})\n"

            board_context_info += """
CONTEXT-AWARE CAPABILITIES:
With this detailed board layout, you can now:
- Answer questions about specific cards without function calls (e.g., "What's in the To Do list?")
- Provide summaries of board content (e.g., "Summarize my current tasks")
- Compare lists and their contents (e.g., "How many tasks are in each list?")
- Identify priority tasks (e.g., "What are my high priority tasks?")
- Suggest task organization improvements
- Answer questions about task distribution and workload

IMPORTANT CONTEXT RULES:
- When user says "add a list" or "create a list" without specifying a board, use the CURRENT board
- When user mentions a list name (even with typos), try to match it with lists in the CURRENT board first
- When user says "add a task/card" without specifying a list, ask which list in the CURRENT board
- Handle typos intelligently by finding the closest match in the current board's lists
- For ambiguous references like "my list" or "that list", use context from recent conversation and current board
- Always prioritize the current board context unless user explicitly mentions a different board
- Use the detailed card information to answer questions without function calls when possible
- Reference specific card IDs when suggesting actions on cards
"""
        else:
            board_context_info = """
CURRENT BOARD CONTEXT: 
No board is currently selected. User needs to select a board first or you should help them create one.
"""

        # Create comprehensive system message with current board context
        system_message = f"""You are a helpful AI assistant for Task Tiles, a Kanban-style task management system. 
        You're helping user '{user.username}' manage their work.

        IMPORTANT TERMINOLOGY:
        - **BOARD**: A workspace/project container (like "Marketing Campaign" or "Personal Projects")
        - **LIST**: A column within a board representing workflow stages (like "To Do", "In Progress", "Done")
        - **CARD/TASK**: Individual work items within lists (like "Write blog post" or "Fix login bug")

        HIERARCHY: Board → Lists → Cards/Tasks
        Example: "Marketing Campaign" board has lists "Ideas", "In Progress", "Review", "Published"

        {board_context_info}

        YOUR PERSONALITY:
        - Be conversational and friendly
        - Use emojis to make responses engaging
        - Always ask for clarification when information is missing
        - Explain what you're doing and why
        - Provide helpful suggestions
        - Remember our conversation context and refer back to previous messages when relevant
        - Use the current board context to resolve ambiguous references

        CONVERSATION MEMORY:
        - You can reference previous messages in our conversation
        - Build on previous context when users make follow-up requests
        - If a user says "add another one" or "do the same for X", use previous context
        - Remember user preferences and workflow patterns from the conversation

        SMART CONTEXT RESOLUTION:
        - When user mentions a list name, first try to find it in the CURRENT board
        - Handle typos by finding the closest match (e.g., "todoo" → "To Do", "bugs" → "Bug Fixes")
        - For ambiguous references, use current board context and conversation history
        - If user doesn't specify a board, assume they mean the current board
        - Only ask for clarification if you can't reasonably determine what they mean

        ENHANCED CONTEXT AWARENESS:
        - Use the detailed board layout information provided to answer questions directly
        - When user asks "What's in my To Do list?" - list the specific cards from the board context
        - When user asks "Summarize my tasks" or "Summarize the board" - provide a comprehensive summary using the detailed board info
        - When user asks "What are my high priority tasks?" - identify and list high priority cards
        - When user asks "How many tasks do I have?" - count cards from the detailed board layout
        - When user asks "What's in Study Guide?" - look at the board context and list all cards in that list
        - Reference specific card IDs when suggesting actions (e.g., "You could move card #123 to Done")
        - Always check the DETAILED BOARD LAYOUT section above for complete card and list information
        - NEVER say you can't summarize or don't have access to board content when detailed context is provided

        SUMMARIZATION GUIDELINES:
        - Use the detailed board context provided in the system message to answer summary questions
        - When asked to summarize a specific list, extract that list's cards from the board context
        - When asked to summarize the board, provide an overview of all lists and their contents
        - Include card titles, priorities, and descriptions in summaries
        - Count tasks accurately using the provided context data

        WHEN TO USE FUNCTION CALLS vs DIRECT RESPONSES:
        - Use DIRECT RESPONSES for: queries about board content, summaries, counts, priority identification
        - Use FUNCTION CALLS for: creating, moving, deleting, or modifying board items
        - If you have the information in the board context, answer directly without function calls
        - Only use function calls when you need to perform an action or get information not in the current context

        WHEN TO ASK FOR CLARIFICATION:
        - User says "create a task" but current board has no lists
        - User mentions a list that doesn't exist in current board and you can't find a close match
        - User asks about "tasks" but doesn't specify timeframe or location
        - Truly ambiguous requests that can't be resolved with current context

        RESPONSE STYLE:
        - Start with a friendly acknowledgment
        - If you need more info, ask specific questions with examples from the current board
        - If you can help, explain what you're doing and which board/list you're using
        - Use board/list/card terminology consistently
        - Reference current board context naturally
        - Handle typos gracefully without making a big deal about them
        - When providing summaries or lists, use the detailed board information
        - Include specific card names, priorities, and descriptions when relevant

        EXAMPLES OF ENHANCED CONTEXT-AWARE RESPONSES:
        ❌ "I need more information about which board"
        ✅ "I'll add that to your '{current_board_context.board_title if current_board_context else 'current'}' board! Which list would you like me to add it to? You have: {', '.join([lst['title'] for lst in (current_board_context.lists or [])]) if current_board_context else 'various lists'}"

        ❌ "List not found"
        ✅ "I couldn't find a list called 'todoo' but I see you have a 'To Do' list in your {current_board_context.board_title if current_board_context else 'current'} board. Should I add it there?"

        ❌ "I need to call a function to see your tasks"
        ✅ "Looking at your current board, I can see you have 5 tasks in your To Do list: 1. 🔴 'Fix login bug' (high priority), 2. 🟡 'Update homepage'..."

        ❌ "Let me get your board information"
        ✅ "Based on your current board layout, you have 3 high priority tasks: 'Fix login bug' in To Do, 'Review PR' in In Progress, and 'Deploy hotfix' in Done."

        Always be helpful and use the current board context to make interactions as smooth as possible."""

        # Build conversation messages including history
        messages = [{"role": "system", "content": system_message}]

        # Add conversation history (keep last 10 messages to avoid token limits)
        recent_history = conversation_history[-10:] if conversation_history else []
        for hist_msg in recent_history:
            if hist_msg.role in ["user", "assistant"]:
                messages.append({"role": hist_msg.role, "content": hist_msg.content})

        # Add current message
        messages.append({"role": "user", "content": message})

        # Make OpenAI API call with function calling
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            functions=CHATBOT_FUNCTIONS,
            function_call="auto",
            temperature=0.7,
            max_tokens=1000,  # Increased for more detailed context-aware responses
        )

        message_response = response.choices[0].message

        # Check if OpenAI wants to call a function
        if message_response.function_call:
            function_name = message_response.function_call.name
            function_args = json.loads(message_response.function_call.arguments)

            # Execute the requested function with current board context
            function_result = await execute_chatbot_function(
                function_name, function_args, current_board_context, user, db
            )

            # Build follow-up messages including the function call and result
            follow_up_messages = messages + [
                {
                    "role": "assistant",
                    "content": None,
                    "function_call": {
                        "name": function_name,
                        "arguments": json.dumps(function_args),
                    },
                },
                {
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(function_result),
                },
            ]

            # Get a follow-up response from OpenAI that incorporates the function result
            follow_up_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=follow_up_messages,
                temperature=0.7,
                max_tokens=1000,
            )

            return ChatbotResponse(
                message=follow_up_response.choices[0].message.content,
                action=function_result.get("action"),
                data=function_result.get("data"),
            )
        else:
            # OpenAI provided a direct response without function calling
            return ChatbotResponse(message=message_response.content)

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return ChatbotResponse(
            message="I'm having trouble processing your request right now. Please try again in a moment. 🤔"
        )


async def execute_chatbot_function(
    function_name: str,
    args: dict,
    current_board_context: Optional[CurrentBoardContext],
    user: UserModel,
    db: Session,
) -> dict:
    """Execute the function requested by OpenAI and return results"""

    try:
        if function_name == "get_user_boards":
            return await get_user_boards_function(user, db)

        elif function_name == "get_todays_tasks":
            return await get_todays_tasks_function(user, db)

        elif function_name == "create_board":
            return await create_board_function(
                args.get("board_name"), args.get("description"), user, db
            )

        elif function_name == "create_list":
            return await create_list_function(
                args.get("list_name"),
                args.get("board_name"),
                current_board_context,
                user,
                db,
            )

        elif function_name == "delete_list":
            return await delete_list_function(
                args.get("list_name"),
                args.get("board_name"),
                current_board_context,
                user,
                db,
            )

        elif function_name == "create_card":
            return await create_card_function(
                args.get("card_title"),
                args.get("card_description"),
                args.get("list_name"),
                args.get("priority", "medium"),
                current_board_context,
                user,
                db,
            )

        elif function_name == "move_card":
            return await move_card_function(
                args.get("card_title"),
                args.get("target_list_name"),
                args.get("position", -1),  # Default to bottom if not provided
                current_board_context,
                user,
                db,
            )

        elif function_name == "delete_card":
            return await delete_card_function(
                args.get("card_title"),
                args.get("list_name"),
                current_board_context,
                user,
                db,
            )

        elif function_name == "get_board_info":
            return await get_board_info_function(args.get("board_name"), user, db)

        elif function_name == "get_available_options":
            return await get_available_options_function(user, db)

        else:
            return {"status": "error", "message": f"Unknown function: {function_name}"}

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error executing {function_name}: {str(e)}",
        }


# Updated function implementations for OpenAI integration
async def get_user_boards_function(user: UserModel, db: Session) -> dict:
    """Get user's boards for OpenAI function calling"""
    try:
        user_boards = get_user_boards(user.id, db)

        if not user_boards:
            return {
                "status": "success",
                "message": "You don't have any boards yet! 📋",
                "boards": [],
                "suggestion": "Would you like me to create your first board? Just say something like 'Create a new board called Personal Tasks'",
                "action": "show_boards",
            }

        boards_data = []
        for board in user_boards:
            lists_count = len(board.lists)
            cards_count = sum(len(lst.cards) for lst in board.lists)
            boards_data.append(
                {
                    "id": board.id,
                    "title": board.title,
                    "description": board.description,
                    "type": "Shared" if board.is_shared else "Personal",
                    "lists": lists_count,
                    "cards": cards_count,
                    "members": len(board.members) + 1 if board.is_shared else 1,
                }
            )

        return {
            "status": "success",
            "message": f"You have {len(user_boards)} board{'s' if len(user_boards) != 1 else ''}",
            "boards": boards_data,
            "action": "show_boards",
            "data": {"boards": boards_data},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_todays_tasks_function(user: UserModel, db: Session) -> dict:
    """Get today's tasks for OpenAI function calling"""
    try:
        user_boards = get_user_boards(user.id, db)
        today = datetime.utcnow().date()
        recent_cards = []

        for board in user_boards:
            for task_list in board.lists:
                for card in task_list.cards:
                    card_date = card.created_at.date()
                    has_today_keyword = (
                        "today" in (card.title + " " + (card.description or "")).lower()
                    )

                    if card_date == today or has_today_keyword:
                        recent_cards.append(
                            {
                                "id": card.id,
                                "title": card.title,
                                "board": board.title,
                                "list": task_list.title,
                                "created": card.created_at.strftime("%H:%M"),
                                "priority": (
                                    card.priority.value if card.priority else "medium"
                                ),
                            }
                        )

        return {
            "status": "success",
            "message": f"Found {len(recent_cards)} tasks for today",
            "tasks": recent_cards,
            "action": "show_tasks",
            "data": {"tasks": recent_cards},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def create_board_function(
    board_name: str, description: str, user: UserModel, db: Session
) -> dict:
    """Create board for OpenAI function calling"""
    try:
        new_board = BoardModel(
            title=board_name, description=description, owner_id=user.id
        )
        db.add(new_board)
        db.commit()
        db.refresh(new_board)

        return {
            "status": "success",
            "message": f"Successfully created board '{board_name}'",
            "board_id": new_board.id,
            "board_name": board_name,
            "action": "board_created",
            "data": {"board_id": new_board.id, "board_name": board_name},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def create_list_function(
    list_name: str,
    board_name: str,
    current_board_context: Optional[CurrentBoardContext],
    user: UserModel,
    db: Session,
) -> dict:
    """Create list for OpenAI function calling with current board context awareness"""
    try:
        user_boards = get_user_boards(user.id, db)

        if not user_boards:
            return {
                "status": "error",
                "message": "You don't have any boards yet! You need to create a board first before adding lists.",
                "suggestion": "Try saying 'Create a new board called [Board Name]' first!",
            }

        # Prioritize current board context if available
        target_board = None

        # If user is viewing a board and doesn't specify a different board, use current board
        if current_board_context and current_board_context.board_id and not board_name:
            for board in user_boards:
                if board.id == current_board_context.board_id:
                    target_board = board
                    break

        # If board name is specified, try to find it
        elif board_name:
            # First try exact match
            for board in user_boards:
                if board.title.lower() == board_name.lower():
                    target_board = board
                    break

            # If not found, try fuzzy matching
            if not target_board:
                import difflib

                board_titles = [board.title for board in user_boards]
                close_matches = difflib.get_close_matches(
                    board_name, board_titles, n=1, cutoff=0.6
                )

                if close_matches:
                    # Found a close match
                    for board in user_boards:
                        if board.title == close_matches[0]:
                            target_board = board
                            break

                    return {
                        "status": "clarification",
                        "message": f"I couldn't find a board called '{board_name}', but I found '{close_matches[0]}' which seems similar. Should I add the '{list_name}' list to '{close_matches[0]}'?",
                        "suggested_board": close_matches[0],
                        "action": "clarify_board",
                    }
                else:
                    board_names = [board.title for board in user_boards]
                    return {
                        "status": "error",
                        "message": f"I couldn't find a board called '{board_name}' 🤔",
                        "available_boards": board_names,
                        "suggestion": f"Did you mean one of these boards: {', '.join(board_names)}?",
                    }
        else:
            # No board specified and no current context
            if len(user_boards) == 1:
                target_board = user_boards[0]
            else:
                board_names = [board.title for board in user_boards]
                current_board_hint = ""
                if current_board_context and current_board_context.board_title:
                    current_board_hint = f" (you're currently viewing '{current_board_context.board_title}')"

                return {
                    "status": "clarification_needed",
                    "message": f"I'd be happy to create the '{list_name}' list! 📝 Which board would you like me to add it to{current_board_hint}?",
                    "available_boards": board_names,
                    "current_board": (
                        current_board_context.board_title
                        if current_board_context
                        else None
                    ),
                    "suggestion": f"You have these boards: {', '.join(board_names)}. Just let me know which one!",
                }

        max_position = len(target_board.lists)
        new_list = TaskListModel(
            title=list_name, position=max_position, board_id=target_board.id
        )

        db.add(new_list)
        db.commit()
        db.refresh(new_list)

        context_note = ""
        if current_board_context and current_board_context.board_id == target_board.id:
            context_note = " (your current board)"

        return {
            "status": "success",
            "message": f"Perfect! ✅ I've created the '{list_name}' list in your '{target_board.title}' board{context_note}",
            "list_id": new_list.id,
            "list_name": list_name,
            "board_name": target_board.title,
            "board_id": target_board.id,
            "action": "list_created",
            "data": {
                "list_id": new_list.id,
                "list_name": list_name,
                "board_name": target_board.title,
                "board_id": target_board.id,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delete_list_function(
    list_name: str,
    board_name: str,
    current_board_context: Optional[CurrentBoardContext],
    user: UserModel,
    db: Session,
) -> dict:
    """Delete a list for OpenAI function calling with current board context awareness"""
    try:
        user_boards = get_user_boards(user.id, db)

        if not user_boards:
            return {
                "status": "error",
                "message": "You don't have any boards yet! You need to create a board and list first.",
                "suggestion": "Try saying 'Create a new board called [Board Name]' first!",
            }

        # Prioritize current board
        current_board = None
        if current_board_context and current_board_context.board_id:
            for board in user_boards:
                if board.id == current_board_context.board_id:
                    current_board = board
                    break

        # If no current board, use first board
        if not current_board:
            current_board = user_boards[0]

        # Find the list to delete
        target_list = None

        # First try exact match
        for lst in current_board.lists:
            if lst.title.lower() == list_name.lower():
                target_list = lst
                break

        if not target_list:
            # Try fuzzy matching
            import difflib

            list_titles = [lst.title for lst in current_board.lists]
            close_matches = difflib.get_close_matches(
                list_name, list_titles, n=1, cutoff=0.6
            )

            if close_matches:
                return {
                    "status": "clarification",
                    "message": f"I couldn't find a list called '{list_name}', but I found '{close_matches[0]}' which seems similar. Should I delete that list?",
                    "suggested_list": close_matches[0],
                    "suggested_board": current_board.title,
                    "action": "clarify_list",
                }
            else:
                available_lists = [lst.title for lst in current_board.lists]
                return {
                    "status": "error",
                    "message": f"I couldn't find a list called '{list_name}' in your '{current_board.title}' board.",
                    "available_lists": available_lists,
                    "suggestion": f"Available lists: {', '.join(available_lists[:3])}{'...' if len(available_lists) > 3 else ''}",
                }

        # Get the actual list from database
        list_to_delete = (
            db.query(TaskListModel).filter(TaskListModel.id == target_list.id).first()
        )

        if not list_to_delete:
            return {
                "status": "error",
                "message": f"List '{list_name}' not found.",
            }

        # Check if user has permission to delete (owner of board)
        if not has_board_access(user.id, current_board.id, db):
            return {
                "status": "error",
                "message": "You don't have permission to delete lists from this board.",
            }

        # Count cards that will be deleted
        cards_count = (
            db.query(CardModel).filter(CardModel.list_id == target_list.id).count()
        )

        # Store list info before deletion
        deleted_list_id = list_to_delete.id
        deleted_list_title = list_to_delete.title

        # Delete the list (this will cascade delete all cards in the list)
        db.delete(list_to_delete)
        db.commit()

        return {
            "status": "success",
            "message": f"Perfect! ✅ I've deleted the list '{deleted_list_title}' from the '{current_board.title}' board. This also deleted {cards_count} card(s) that were in the list.",
            "list_id": deleted_list_id,
            "list_name": deleted_list_title,
            "board_name": current_board.title,
            "board_id": current_board.id,
            "cards_deleted": cards_count,
            "action": "list_deleted",
            "data": {
                "list_id": deleted_list_id,
                "list_name": deleted_list_title,
                "board_name": current_board.title,
                "board_id": current_board.id,
                "cards_deleted": cards_count,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def create_card_function(
    card_title: str,
    card_description: str,
    list_name: str,
    priority: str,
    current_board_context: Optional[CurrentBoardContext],
    user: UserModel,
    db: Session,
) -> dict:
    """Create card for OpenAI function calling with current board context awareness"""
    try:
        user_boards = get_user_boards(user.id, db)

        if not user_boards:
            return {
                "status": "error",
                "message": "You don't have any boards yet! You need to create a board and list first.",
                "suggestion": "Try saying 'Create a new board called [Board Name]' first!",
            }

        # Prioritize current board for finding lists
        target_lists = []
        current_board = None

        # If user is viewing a board, prioritize lists from that board
        if current_board_context and current_board_context.board_id:
            for board in user_boards:
                if board.id == current_board_context.board_id:
                    current_board = board
                    for lst in board.lists:
                        target_lists.append(
                            {"list": lst, "board": board, "is_current_board": True}
                        )
                    break

        # Add lists from other boards
        for board in user_boards:
            if not current_board or board.id != current_board.id:
                for lst in board.lists:
                    target_lists.append(
                        {"list": lst, "board": board, "is_current_board": False}
                    )

        if not target_lists:
            current_board_hint = ""
            if current_board_context and current_board_context.board_title:
                current_board_hint = (
                    f" in your '{current_board_context.board_title}' board"
                )

            return {
                "status": "error",
                "message": f"You don't have any lists yet{current_board_hint}! You need to create a list first before adding tasks.",
                "suggestion": "Try saying 'Create a new list called To Do' first!",
            }

        # Find target list with smart matching
        target_list_info = None

        if list_name:
            # First try exact match in current board
            if current_board:
                for list_info in target_lists:
                    if (
                        list_info["is_current_board"]
                        and list_info["list"].title.lower() == list_name.lower()
                    ):
                        target_list_info = list_info
                        break

            # If not found in current board, try exact match in all boards
            if not target_list_info:
                for list_info in target_lists:
                    if list_info["list"].title.lower() == list_name.lower():
                        target_list_info = list_info
                        break

            # If still not found, try fuzzy matching
            if not target_list_info:
                import difflib

                # Prioritize current board lists for fuzzy matching
                current_board_lists = [
                    info["list"].title
                    for info in target_lists
                    if info["is_current_board"]
                ]
                all_lists = [info["list"].title for info in target_lists]

                # Try fuzzy match in current board first
                close_matches = []
                if current_board_lists:
                    close_matches = difflib.get_close_matches(
                        list_name, current_board_lists, n=1, cutoff=0.6
                    )

                # If no good match in current board, try all lists
                if not close_matches:
                    close_matches = difflib.get_close_matches(
                        list_name, all_lists, n=1, cutoff=0.6
                    )

                if close_matches:
                    # Found a close match
                    for list_info in target_lists:
                        if list_info["list"].title == close_matches[0]:
                            target_list_info = list_info
                            break

                    board_hint = ""
                    if target_list_info["is_current_board"]:
                        board_hint = " (in your current board)"
                    else:
                        board_hint = f" (in '{target_list_info['board'].title}')"

                    return {
                        "status": "clarification",
                        "message": f"I couldn't find a list called '{list_name}', but I found '{close_matches[0]}'{board_hint} which seems similar. Should I add the task there?",
                        "suggested_list": close_matches[0],
                        "suggested_board": target_list_info["board"].title,
                        "action": "clarify_list",
                    }
                else:
                    # No close match found
                    current_board_lists_str = ""
                    if current_board and current_board_context:
                        current_lists = [
                            info["list"].title
                            for info in target_lists
                            if info["is_current_board"]
                        ]
                        if current_lists:
                            current_board_lists_str = f" In your current board '{current_board_context.board_title}', you have: {', '.join(current_lists)}."

                    all_available_lists = [
                        f"'{info['list'].title}' (in {info['board'].title})"
                        for info in target_lists[
                            :5
                        ]  # Show first 5 to avoid overwhelming
                    ]

                    return {
                        "status": "error",
                        "message": f"I couldn't find a list called '{list_name}' 🤔{current_board_lists_str}",
                        "available_lists": all_available_lists,
                        "suggestion": f"Available lists: {', '.join(all_available_lists[:3])}{'...' if len(all_available_lists) > 3 else ''}",
                    }
        else:
            # No list specified - ask for clarification with current board prioritized
            if (
                current_board
                and len([info for info in target_lists if info["is_current_board"]]) > 0
            ):
                current_board_lists = [
                    f"'{info['list'].title}'"
                    for info in target_lists
                    if info["is_current_board"]
                ]

                return {
                    "status": "clarification_needed",
                    "message": f"I'd be happy to create the task '{card_title}' for you! 📝 Which list in your '{current_board_context.board_title}' board should I add it to?",
                    "available_lists": current_board_lists,
                    "current_board": current_board_context.board_title,
                    "suggestion": f"You have these lists in your current board: {', '.join(current_board_lists)}. Just let me know which one!",
                }
            else:
                # Multiple boards and lists
                all_available_lists = [
                    f"'{info['list'].title}' (in {info['board'].title})"
                    for info in target_lists[:5]
                ]

                return {
                    "status": "clarification_needed",
                    "message": f"I'd be happy to create the task '{card_title}' for you! 📝 Which list would you like me to add it to?",
                    "available_lists": all_available_lists,
                    "suggestion": f"You have these lists: {', '.join(all_available_lists[:3])}{'...' if len(all_available_lists) > 3 else ''}. Just let me know which one!",
                }

        target_list = target_list_info["list"]
        target_board = target_list_info["board"]

        max_position = len(target_list.cards)

        from models import Priority

        priority_enum = Priority.MEDIUM
        if priority:
            try:
                priority_enum = Priority(priority.lower())
            except ValueError:
                priority_enum = Priority.MEDIUM

        new_card = CardModel(
            title=card_title,
            description=card_description,
            list_id=target_list.id,
            position=max_position,
            created_by=user.id,
            checklist=[],
            priority=priority_enum,
        )

        db.add(new_card)
        db.commit()
        db.refresh(new_card)

        # Add creator as contributor
        contributor = CardContributorModel(card_id=new_card.id, user_id=user.id)
        db.add(contributor)
        db.commit()

        priority_display = priority.title() if priority else "Medium"

        # Add context note
        context_note = ""
        if target_list_info["is_current_board"]:
            context_note = " (in your current board)"

        return {
            "status": "success",
            "message": f"Excellent! ✅ I've created the task '{card_title}' in your '{target_list.title}' list on the '{target_board.title}' board{context_note}. Priority is set to {priority_display}.",
            "card_id": new_card.id,
            "card_title": card_title,
            "list_name": target_list.title,
            "board_name": target_board.title,
            "board_id": target_board.id,
            "priority": priority_display,
            "action": "card_created",
            "data": {
                "card_id": new_card.id,
                "card_title": card_title,
                "list_name": target_list.title,
                "board_name": target_board.title,
                "board_id": target_board.id,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def move_card_function(
    card_title: str,
    target_list_name: str,
    position: int,
    current_board_context: Optional[CurrentBoardContext],
    user: UserModel,
    db: Session,
) -> dict:
    """Move a card for OpenAI function calling with current board context awareness"""
    try:
        user_boards = get_user_boards(user.id, db)

        if not user_boards:
            return {
                "status": "error",
                "message": "You don't have any boards yet! You need to create a board and list first.",
                "suggestion": "Try saying 'Create a new board called [Board Name]' first!",
            }

        # Prioritize current board for finding lists
        target_lists = []
        current_board = None

        # If user is viewing a board, prioritize lists from that board
        if current_board_context and current_board_context.board_id:
            for board in user_boards:
                if board.id == current_board_context.board_id:
                    current_board = board
                    for lst in board.lists:
                        target_lists.append(
                            {"list": lst, "board": board, "is_current_board": True}
                        )
                    break

        # Add lists from other boards
        for board in user_boards:
            if not current_board or board.id != current_board.id:
                for lst in board.lists:
                    target_lists.append(
                        {"list": lst, "board": board, "is_current_board": False}
                    )

        if not target_lists:
            current_board_hint = ""
            if current_board_context and current_board_context.board_title:
                current_board_hint = (
                    f" in your '{current_board_context.board_title}' board"
                )

            return {
                "status": "error",
                "message": f"You don't have any lists yet{current_board_hint}! You need to create a list first before adding tasks.",
                "suggestion": "Try saying 'Create a new list called To Do' first!",
            }

        # Find target list with smart matching
        target_list_info = None

        if target_list_name:
            # First try exact match in current board
            if current_board:
                for list_info in target_lists:
                    if (
                        list_info["is_current_board"]
                        and list_info["list"].title.lower() == target_list_name.lower()
                    ):
                        target_list_info = list_info
                        break

            # If not found in current board, try exact match in all boards
            if not target_list_info:
                for list_info in target_lists:
                    if list_info["list"].title.lower() == target_list_name.lower():
                        target_list_info = list_info
                        break

            # If still not found, try fuzzy matching
            if not target_list_info:
                import difflib

                # Prioritize current board lists for fuzzy matching
                current_board_lists = [
                    info["list"].title
                    for info in target_lists
                    if info["is_current_board"]
                ]
                all_lists = [info["list"].title for info in target_lists]

                # Try fuzzy match in current board first
                close_matches = []
                if current_board_lists:
                    close_matches = difflib.get_close_matches(
                        target_list_name, current_board_lists, n=1, cutoff=0.6
                    )

                # If no good match in current board, try all lists
                if not close_matches:
                    close_matches = difflib.get_close_matches(
                        target_list_name, all_lists, n=1, cutoff=0.6
                    )

                if close_matches:
                    # Found a close match
                    for list_info in target_lists:
                        if list_info["list"].title == close_matches[0]:
                            target_list_info = list_info
                            break

                    board_hint = ""
                    if target_list_info["is_current_board"]:
                        board_hint = " (in your current board)"
                    else:
                        board_hint = f" (in '{target_list_info['board'].title}')"

                    return {
                        "status": "clarification",
                        "message": f"I couldn't find a list called '{target_list_name}', but I found '{close_matches[0]}'{board_hint} which seems similar. Should I move the card there?",
                        "suggested_list": close_matches[0],
                        "suggested_board": target_list_info["board"].title,
                        "action": "clarify_list",
                    }
                else:
                    # No close match found
                    current_board_lists_str = ""
                    if current_board and current_board_context:
                        current_lists = [
                            info["list"].title
                            for info in target_lists
                            if info["is_current_board"]
                        ]
                        if current_lists:
                            current_board_lists_str = f" In your current board '{current_board_context.board_title}', you have: {', '.join(current_lists)}."

                    all_available_lists = [
                        f"'{info['list'].title}' (in {info['board'].title})"
                        for info in target_lists[
                            :5
                        ]  # Show first 5 to avoid overwhelming
                    ]

                    return {
                        "status": "error",
                        "message": f"I couldn't find a list called '{target_list_name}' 🤔{current_board_lists_str}",
                        "available_lists": all_available_lists,
                        "suggestion": f"Available lists: {', '.join(all_available_lists[:3])}{'...' if len(all_available_lists) > 3 else ''}",
                    }
        else:
            # No list specified - ask for clarification with current board prioritized
            if (
                current_board
                and len([info for info in target_lists if info["is_current_board"]]) > 0
            ):
                current_board_lists = [
                    f"'{info['list'].title}'"
                    for info in target_lists
                    if info["is_current_board"]
                ]

                return {
                    "status": "clarification_needed",
                    "message": f"I'd be happy to move the card '{card_title}' for you! 📝 Which list in your '{current_board_context.board_title}' board should I move it to?",
                    "available_lists": current_board_lists,
                    "current_board": current_board_context.board_title,
                    "suggestion": f"You have these lists in your current board: {', '.join(current_board_lists)}. Just let me know which one!",
                }
            else:
                # Multiple boards and lists
                all_available_lists = [
                    f"'{info['list'].title}' (in {info['board'].title})"
                    for info in target_lists[:5]
                ]

                return {
                    "status": "clarification_needed",
                    "message": f"I'd be happy to move the card '{card_title}' for you! 📝 Which list would you like me to move it to?",
                    "available_lists": all_available_lists,
                    "suggestion": f"You have these lists: {', '.join(all_available_lists[:3])}{'...' if len(all_available_lists) > 3 else ''}. Just let me know which one!",
                }

        target_list = target_list_info["list"]
        target_board = target_list_info["board"]

        # Find the card to move (search in current board, not target list)
        current_board_id = target_board.id
        card_to_move = None

        # Search all lists in the current board for the card
        all_lists_in_board = (
            db.query(TaskListModel)
            .filter(TaskListModel.board_id == current_board_id)
            .all()
        )
        for lst in all_lists_in_board:
            card = (
                db.query(CardModel)
                .filter(CardModel.list_id == lst.id)
                .filter(CardModel.title.ilike(f"%{card_title}%"))
                .first()
            )
            if card:
                card_to_move = card
                break

        if not card_to_move:
            # Get all cards in the board for suggestions
            all_cards_in_board = []
            for lst in all_lists_in_board:
                cards_in_list = (
                    db.query(CardModel).filter(CardModel.list_id == lst.id).all()
                )
                for card in cards_in_list:
                    all_cards_in_board.append(f"'{card.title}' (in {lst.title})")

            return {
                "status": "error",
                "message": f"I couldn't find a card with the title '{card_title}' in the '{target_board.title}' board.",
                "available_cards": all_cards_in_board[:10],  # Show first 10 cards
                "suggestion": f"Available cards: {', '.join([c.split(' (in ')[0] for c in all_cards_in_board[:3]])}{'...' if len(all_cards_in_board) > 3 else ''}",
            }

        old_list_id = card_to_move.list_id
        old_position = card_to_move.position

        # Calculate new position
        if position == -1:
            new_position = len(target_list.cards)  # Bottom of target list
        else:
            new_position = min(
                position, len(target_list.cards)
            )  # Ensure position is valid

        # Update positions of other cards
        if old_list_id != target_list.id:
            # Moving between different lists
            # Move cards up in the old list
            db.query(CardModel).filter(
                CardModel.list_id == old_list_id, CardModel.position > old_position
            ).update({"position": CardModel.position - 1})

            # Move cards down in the new list to make room
            db.query(CardModel).filter(
                CardModel.list_id == target_list.id,
                CardModel.position >= new_position,
            ).update({"position": CardModel.position + 1})
        else:
            # Moving within the same list
            if new_position > old_position:
                # Moving down in the list
                db.query(CardModel).filter(
                    CardModel.list_id == old_list_id,
                    CardModel.position > old_position,
                    CardModel.position <= new_position,
                ).update({"position": CardModel.position - 1})
            elif new_position < old_position:
                # Moving up in the list
                db.query(CardModel).filter(
                    CardModel.list_id == old_list_id,
                    CardModel.position >= new_position,
                    CardModel.position < old_position,
                ).update({"position": CardModel.position + 1})

        # Update the card
        card_to_move.list_id = target_list.id
        card_to_move.position = new_position

        # Add user as contributor for moving the card
        existing_contributor = (
            db.query(CardContributorModel)
            .filter(
                CardContributorModel.card_id == card_to_move.id,
                CardContributorModel.user_id == user.id,
            )
            .first()
        )

        if not existing_contributor:
            contributor = CardContributorModel(card_id=card_to_move.id, user_id=user.id)
            db.add(contributor)

        db.commit()
        db.refresh(card_to_move)

        return {
            "status": "success",
            "message": f"Perfect! ✅ I've moved the card '{card_to_move.title}' to the '{target_list.title}' list on the '{target_board.title}' board.",
            "card_id": card_to_move.id,
            "card_title": card_to_move.title,
            "list_name": target_list.title,
            "board_name": target_board.title,
            "board_id": target_board.id,
            "action": "card_moved",
            "data": {
                "card_id": card_to_move.id,
                "card_title": card_to_move.title,
                "list_name": target_list.title,
                "board_name": target_board.title,
                "board_id": target_board.id,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delete_card_function(
    card_title: str,
    list_name: str,
    current_board_context: Optional[CurrentBoardContext],
    user: UserModel,
    db: Session,
) -> dict:
    """Delete a card for OpenAI function calling with current board context awareness"""
    try:
        user_boards = get_user_boards(user.id, db)

        if not user_boards:
            return {
                "status": "error",
                "message": "You don't have any boards yet! You need to create a board and list first.",
                "suggestion": "Try saying 'Create a new board called [Board Name]' first!",
            }

        # Prioritize current board
        current_board = None
        if current_board_context and current_board_context.board_id:
            for board in user_boards:
                if board.id == current_board_context.board_id:
                    current_board = board
                    break

        # If no current board, use first board
        if not current_board:
            current_board = user_boards[0]

        # If list_name is not specified, search all lists in current board
        if not list_name:
            # Search all lists in the current board for the card
            all_lists_in_board = (
                db.query(TaskListModel)
                .filter(TaskListModel.board_id == current_board.id)
                .all()
            )
            card_to_delete = None
            source_list = None

            for lst in all_lists_in_board:
                card = (
                    db.query(CardModel)
                    .filter(CardModel.list_id == lst.id)
                    .filter(CardModel.title.ilike(f"%{card_title}%"))
                    .first()
                )
                if card:
                    card_to_delete = card
                    source_list = lst
                    break

            if not card_to_delete:
                # Get all cards in the board for suggestions
                all_cards_in_board = []
                for lst in all_lists_in_board:
                    cards_in_list = (
                        db.query(CardModel).filter(CardModel.list_id == lst.id).all()
                    )
                    for card in cards_in_list:
                        all_cards_in_board.append(f"'{card.title}' (in {lst.title})")

                return {
                    "status": "error",
                    "message": f"I couldn't find a card with the title '{card_title}' in the '{current_board.title}' board.",
                    "available_cards": all_cards_in_board[:10],  # Show first 10 cards
                    "suggestion": f"Available cards: {', '.join([c.split(' (in ')[0] for c in all_cards_in_board[:3]])}{'...' if len(all_cards_in_board) > 3 else ''}",
                }
        else:
            # Find specific list first
            target_list = None
            for lst in current_board.lists:
                if lst.title.lower() == list_name.lower():
                    target_list = lst
                    break

            if not target_list:
                # Try fuzzy matching
                import difflib

                list_titles = [lst.title for lst in current_board.lists]
                close_matches = difflib.get_close_matches(
                    list_name, list_titles, n=1, cutoff=0.6
                )

                if close_matches:
                    return {
                        "status": "clarification",
                        "message": f"I couldn't find a list called '{list_name}', but I found '{close_matches[0]}' which seems similar. Should I delete the card from there?",
                        "suggested_list": close_matches[0],
                        "suggested_board": current_board.title,
                        "action": "clarify_list",
                    }
                else:
                    available_lists = [lst.title for lst in current_board.lists]
                    return {
                        "status": "error",
                        "message": f"I couldn't find a list called '{list_name}' in your '{current_board.title}' board.",
                        "available_lists": available_lists,
                        "suggestion": f"Available lists: {', '.join(available_lists[:3])}{'...' if len(available_lists) > 3 else ''}",
                    }

            # Search for card in the specific list
            card_to_delete = (
                db.query(CardModel)
                .filter(CardModel.list_id == target_list.id)
                .filter(CardModel.title.ilike(f"%{card_title}%"))
                .first()
            )
            source_list = target_list

            if not card_to_delete:
                # Show cards from specified list
                all_cards = [f"'{c.title}'" for c in target_list.cards]
                return {
                    "status": "error",
                    "message": f"I couldn't find a card with the title '{card_title}' in the '{target_list.title}' list.",
                    "available_cards": all_cards[:10],  # Show first 10 cards
                    "suggestion": f"Available cards: {', '.join(all_cards[:3])}{'...' if len(all_cards) > 3 else ''}",
                }

        # Update positions of cards after the deleted card
        old_position = card_to_delete.position
        db.query(CardModel).filter(
            CardModel.list_id == source_list.id, CardModel.position > old_position
        ).update({"position": CardModel.position - 1})

        # Add user as contributor for deleting the card (before deletion)
        existing_contributor = (
            db.query(CardContributorModel)
            .filter(
                CardContributorModel.card_id == card_to_delete.id,
                CardContributorModel.user_id == user.id,
            )
            .first()
        )

        if not existing_contributor:
            contributor = CardContributorModel(
                card_id=card_to_delete.id, user_id=user.id
            )
            db.add(contributor)

        # Store card info before deletion
        deleted_card_id = card_to_delete.id
        deleted_card_title = card_to_delete.title

        # Delete the card
        db.delete(card_to_delete)
        db.commit()

        return {
            "status": "success",
            "message": f"Perfect! ✅ I've deleted the card '{deleted_card_title}' from the '{source_list.title}' list on the '{current_board.title}' board.",
            "card_id": deleted_card_id,
            "card_title": deleted_card_title,
            "list_name": source_list.title,
            "board_name": current_board.title,
            "board_id": current_board.id,
            "action": "card_deleted",
            "data": {
                "card_id": deleted_card_id,
                "card_title": deleted_card_title,
                "list_name": source_list.title,
                "board_name": current_board.title,
                "board_id": current_board.id,
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_board_info_function(
    board_name: str, user: UserModel, db: Session
) -> dict:
    """Get board information for OpenAI function calling"""
    try:
        user_boards = get_user_boards(user.id, db)

        if not user_boards:
            return {"status": "error", "message": "No boards found"}

        # Find target board
        target_board = user_boards[0]  # Default to first board
        if board_name:
            for board in user_boards:
                if board.title.lower() == board_name.lower():
                    target_board = board
                    break

        lists_info = []
        for lst in target_board.lists:
            lists_info.append({"name": lst.title, "cards": len(lst.cards)})

        board_data = {
            "id": target_board.id,
            "title": target_board.title,
            "description": target_board.description,
            "type": "Shared" if target_board.is_shared else "Personal",
            "lists": len(target_board.lists),
            "total_cards": sum(len(lst.cards) for lst in target_board.lists),
            "members": len(target_board.members) + 1 if target_board.is_shared else 1,
            "created": target_board.created_at.strftime("%B %d, %Y"),
            "lists_info": lists_info,
        }

        return {
            "status": "success",
            "message": f"Board information for '{target_board.title}'",
            "board": board_data,
            "action": "board_info",
            "data": {"board_id": target_board.id, "board_name": target_board.title},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_available_options_function(user: UserModel, db: Session) -> dict:
    """Get available boards and lists to help with decision making"""
    try:
        user_boards = get_user_boards(user.id, db)

        if not user_boards:
            return {
                "status": "success",
                "message": "No boards found. You'll need to create your first board!",
                "boards": [],
                "suggestion": "Try saying 'Create a new board called [Your Board Name]'",
                "action": "show_options",
            }

        boards_info = []
        for board in user_boards:
            lists_info = []
            for lst in board.lists:
                lists_info.append({"name": lst.title, "card_count": len(lst.cards)})

            boards_info.append(
                {
                    "name": board.title,
                    "description": board.description,
                    "lists": lists_info,
                    "total_cards": sum(len(lst.cards) for lst in board.lists),
                }
            )

        return {
            "status": "success",
            "message": f"Here are your available options:",
            "boards": boards_info,
            "total_boards": len(user_boards),
            "action": "show_options",
            "data": {"boards": boards_info},
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/chatbot/voice-to-text")
async def voice_to_text(
    audio: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Convert audio to text using OpenAI Whisper"""

    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    # Validate file type
    if not audio.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload an audio file."
        )

    try:
        # Read audio data
        audio_data = await audio.read()

        # Create a temporary file-like object for OpenAI
        import io

        audio_file = io.BytesIO(audio_data)
        audio_file.name = audio.filename or "audio.wav"

        # Transcribe using Whisper
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, response_format="text"
        )

        return {"text": transcript}

    except Exception as e:
        print(f"Whisper transcription error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to transcribe audio. Please try again."
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
