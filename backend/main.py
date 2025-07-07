from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import json
import os

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
    BoardRole
)
from auth import (
    authenticate_user, 
    create_access_token, 
    get_current_active_user, 
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Task Tiles API", description="A collaborative Kanban-style task management API")

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


class CardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    checklist: Optional[List[str]] = None


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


# Helper functions
def has_board_access(user_id: int, board_id: int, db: Session) -> bool:
    """Check if user has access to board (owner or member)"""
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board:
        return False
    
    if board.owner_id == user_id:
        return True
    
    membership = db.query(BoardMemberModel).filter(
        BoardMemberModel.board_id == board_id,
        BoardMemberModel.user_id == user_id
    ).first()
    
    return membership is not None


def get_user_boards(user_id: int, db: Session):
    """Get all boards user has access to (owned + member of)"""
    # Get owned boards
    owned_boards = db.query(BoardModel).filter(BoardModel.owner_id == user_id).all()
    
    # Get boards user is member of
    memberships = db.query(BoardMemberModel).filter(BoardMemberModel.user_id == user_id).all()
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
    member_records = db.query(BoardMemberModel).filter(BoardMemberModel.board_id == board.id).all()
    for member_record in member_records:
        members.append({
            "id": member_record.user.id,
            "username": member_record.user.username,
            "email": member_record.user.email,
            "full_name": member_record.user.full_name,
            "avatar_url": member_record.user.avatar_url,
            "is_active": member_record.user.is_active
        })
    
    # Get lists for this board
    lists = db.query(TaskListModel).filter(TaskListModel.board_id == board.id).order_by(TaskListModel.position).all()
    
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
            "is_active": board.owner.is_active
        },
        "members": members,
        "is_shared": len(members) > 0,
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
            "cards": []
        }
        
        for card in cards:
            # Get contributors
            contributors = []
            contributor_records = db.query(CardContributorModel).filter(CardContributorModel.card_id == card.id).all()
            for contrib in contributor_records:
                contributors.append({
                    "id": contrib.user.id,
                    "username": contrib.user.username,
                    "full_name": contrib.user.full_name,
                    "avatar_url": contrib.user.avatar_url,
                    "contributed_at": contrib.contributed_at.isoformat()
                })
            
            card_data = {
                "id": card.id,
                "title": card.title,
                "description": card.description,
                "list_id": card.list_id,
                "position": card.position,
                "checklist": card.checklist or [],
                "created_at": card.created_at.isoformat(),
                "updated_at": card.updated_at.isoformat(),
                "creator": {
                    "id": card.creator.id,
                    "username": card.creator.username,
                    "email": card.creator.email,
                    "full_name": card.creator.full_name,
                    "avatar_url": card.creator.avatar_url,
                    "is_active": card.creator.is_active
                },
                "contributors": contributors
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


@app.get("/api/me", response_model=UserProfile)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user


@app.put("/api/me", response_model=UserProfile)
async def update_user_profile(user_update: UserUpdate, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Update user profile"""
    if user_update.email and user_update.email != current_user.email:
        # Check if email is already taken
        existing_user = db.query(UserModel).filter(UserModel.email == user_update.email, UserModel.id != current_user.id).first()
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
async def update_password(password_update: PasswordUpdate, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Update user password"""
    from auth import verify_password
    
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.hashed_password = get_password_hash(password_update.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}


# Board endpoints
@app.get("/api/boards", response_model=List[Board])
async def get_boards(current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get all boards user has access to"""
    boards = get_user_boards(current_user.id, db)
    
    board_list = []
    for board in boards:
        board_data = build_board_data(board, db)
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
    
    return build_board_data(board, db)


@app.get("/api/boards/{board_id}", response_model=Board)
async def get_board(board_id: int, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get a specific board with all its lists and cards"""
    if not has_board_access(current_user.id, board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")
    
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    return build_board_data(board, db)


@app.post("/api/boards/{board_id}/invite")
async def invite_user_to_board(board_id: int, invitation: BoardInvite, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Invite a user to collaborate on a board"""
    board = db.query(BoardModel).filter(BoardModel.id == board_id, BoardModel.owner_id == current_user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found or you don't have permission")
    
    # Find the user to invite
    invitee = db.query(UserModel).filter(UserModel.username == invitation.username).first()
    if not invitee:
        raise HTTPException(status_code=404, detail="User not found")
    
    if invitee.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")
    
    # Check if user is already a member or has pending invitation
    existing_member = db.query(BoardMemberModel).filter(
        BoardMemberModel.board_id == board_id,
        BoardMemberModel.user_id == invitee.id
    ).first()
    
    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member of this board")
    
    existing_invitation = db.query(InvitationModel).filter(
        InvitationModel.board_id == board_id,
        InvitationModel.invitee_id == invitee.id,
        InvitationModel.status == InvitationStatus.PENDING
    ).first()
    
    if existing_invitation:
        raise HTTPException(status_code=400, detail="User already has a pending invitation")
    
    # Create invitation
    new_invitation = InvitationModel(
        board_id=board_id,
        inviter_id=current_user.id,
        invitee_id=invitee.id,
        message=invitation.message
    )
    
    db.add(new_invitation)
    db.commit()
    
    return {"message": f"Invitation sent to {invitation.username}"}


@app.get("/api/invitations", response_model=List[Invitation])
async def get_user_invitations(current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get pending invitations for current user"""
    invitations = db.query(InvitationModel).filter(
        InvitationModel.invitee_id == current_user.id,
        InvitationModel.status == InvitationStatus.PENDING
    ).all()
    
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
                "is_active": invitation.inviter.is_active
            },
            "message": invitation.message,
            "status": invitation.status.value,
            "created_at": invitation.created_at.isoformat()
        }
        invitation_list.append(invitation_data)
    
    return invitation_list


@app.post("/api/invitations/{invitation_id}/respond")
async def respond_to_invitation(invitation_id: int, response: InvitationResponse, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Accept or decline a board invitation"""
    invitation = db.query(InvitationModel).filter(
        InvitationModel.id == invitation_id,
        InvitationModel.invitee_id == current_user.id,
        InvitationModel.status == InvitationStatus.PENDING
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    if response.accept:
        # Accept invitation - add user as board member
        board_member = BoardMemberModel(
            board_id=invitation.board_id,
            user_id=current_user.id,
            role=BoardRole.MEMBER
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
async def create_list(list_data: ListCreate, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Create a new list"""
    if not has_board_access(current_user.id, list_data.board_id, db):
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
    # Verify the list exists and user has access
    task_list = db.query(TaskListModel).filter(TaskListModel.id == card_data.list_id).first()
    if not task_list:
        raise HTTPException(status_code=404, detail="List not found")
    
    if not has_board_access(current_user.id, task_list.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Calculate new position (last in the list)
    max_position = db.query(CardModel).filter(CardModel.list_id == card_data.list_id).count()
    
    # Create new card
    new_card = CardModel(
        title=card_data.title,
        description=card_data.description,
        list_id=card_data.list_id,
        position=max_position,
        created_by=current_user.id,
        checklist=[]
    )
    
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    
    # Add creator as contributor
    contributor = CardContributorModel(
        card_id=new_card.id,
        user_id=current_user.id
    )
    db.add(contributor)
    db.commit()
    
    return build_card_data(new_card, db)


@app.put("/api/cards/{card_id}", response_model=Card)
async def update_card(card_id: int, card_update: CardUpdate, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
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
    
    card.updated_at = datetime.utcnow()
    
    # Add user as contributor if not already
    existing_contributor = db.query(CardContributorModel).filter(
        CardContributorModel.card_id == card_id,
        CardContributorModel.user_id == current_user.id
    ).first()
    
    if not existing_contributor:
        contributor = CardContributorModel(
            card_id=card_id,
            user_id=current_user.id
        )
        db.add(contributor)
    
    db.commit()
    db.refresh(card)
    
    return build_card_data(card, db)


def build_card_data(card: CardModel, db: Session):
    """Build complete card data with creator and contributors"""
    # Get contributors
    contributors = []
    contributor_records = db.query(CardContributorModel).filter(CardContributorModel.card_id == card.id).all()
    for contrib in contributor_records:
        contributors.append({
            "id": contrib.user.id,
            "username": contrib.user.username,
            "full_name": contrib.user.full_name,
            "avatar_url": contrib.user.avatar_url,
            "contributed_at": contrib.contributed_at.isoformat()
        })
    
    return {
        "id": card.id,
        "title": card.title,
        "description": card.description,
        "list_id": card.list_id,
        "position": card.position,
        "checklist": card.checklist or [],
        "created_at": card.created_at.isoformat(),
        "updated_at": card.updated_at.isoformat(),
        "creator": {
            "id": card.creator.id,
            "username": card.creator.username,
            "email": card.creator.email,
            "full_name": card.creator.full_name,
            "avatar_url": card.creator.avatar_url,
            "is_active": card.creator.is_active
        },
        "contributors": contributors
    }


@app.put("/api/cards/{card_id}/move", response_model=Card)
async def move_card(card_id: int, move_data: MoveCard, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Move a card to a different list or position"""
    # Find the card and verify access
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Verify access to source board
    source_list = db.query(TaskListModel).filter(TaskListModel.id == card.list_id).first()
    if not has_board_access(current_user.id, source_list.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Verify target list exists and belongs to same board
    target_list = db.query(TaskListModel).filter(TaskListModel.id == move_data.new_list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")
    
    if source_list.board_id != target_list.board_id:
        raise HTTPException(status_code=400, detail="Cannot move cards between different boards")
    
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
    
    # Add user as contributor for moving the card
    existing_contributor = db.query(CardContributorModel).filter(
        CardContributorModel.card_id == card_id,
        CardContributorModel.user_id == current_user.id
    ).first()
    
    if not existing_contributor:
        contributor = CardContributorModel(
            card_id=card_id,
            user_id=current_user.id
        )
        db.add(contributor)
    
    db.commit()
    db.refresh(card)
    
    return build_card_data(card, db)


@app.delete("/api/boards/{board_id}")
async def delete_board(board_id: int, current_user: UserModel = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Delete a board (only owner can delete)"""
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
    
    if not has_board_access(current_user.id, task_list.board_id, db):
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
    
    # Verify access
    task_list = db.query(TaskListModel).filter(TaskListModel.id == card.list_id).first()
    if not has_board_access(current_user.id, task_list.board_id, db):
        raise HTTPException(status_code=404, detail="Board not found")
    
    db.delete(card)
    db.commit()
    
    return {"message": "Card deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
