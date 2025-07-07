from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

app = FastAPI(title="Task Tiles API", description="A Trello-like task management API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Data models
class Card(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    list_id: int
    position: int = 0
    checklist: List[str] = []


class TaskList(BaseModel):
    id: int
    title: str
    position: int = 0
    cards: List[Card] = []


class Board(BaseModel):
    id: int
    title: str
    lists: List[TaskList] = []


# In-memory storage (we'll replace with database later)
boards_data = []
lists_data = []
cards_data = []


# Initialize with sample data
def init_sample_data():
    global boards_data, lists_data, cards_data

    if not boards_data:
        # Create sample board
        boards_data = [{"id": 1, "title": "My Task Board"}]

        # Create sample lists
        lists_data = [
            {"id": 1, "title": "To Do", "position": 0},
            {"id": 2, "title": "In Progress", "position": 1},
            {"id": 3, "title": "Done", "position": 2},
        ]

        # Create sample cards
        cards_data = [
            {
                "id": 1,
                "title": "Design wireframes",
                "description": "Create wireframes for the main interface",
                "list_id": 1,
                "position": 0,
                "checklist": [],
            },
            {
                "id": 2,
                "title": "Setup backend",
                "description": "Initialize FastAPI project",
                "list_id": 2,
                "position": 0,
                "checklist": [],
            },
            {
                "id": 3,
                "title": "Create logo",
                "description": "Design company logo",
                "list_id": 3,
                "position": 0,
                "checklist": [],
            },
        ]


# Initialize data on startup
init_sample_data()


@app.get("/")
async def root():
    return {"message": "Task Tiles API is running!"}


@app.get("/api/board")
async def get_board():
    """Get the main board with all lists and cards"""
    # Build the complete board structure
    board = boards_data[0].copy()

    # Add lists to board
    board_lists = []
    for list_item in sorted(lists_data, key=lambda x: x["position"]):
        list_with_cards = list_item.copy()
        # Add cards to list
        list_cards = [card for card in cards_data if card["list_id"] == list_item["id"]]
        list_with_cards["cards"] = sorted(list_cards, key=lambda x: x["position"])
        board_lists.append(list_with_cards)

    board["lists"] = board_lists
    return board


@app.post("/api/lists")
async def create_list(title: str):
    """Create a new list"""
    new_id = max([l["id"] for l in lists_data], default=0) + 1
    new_position = len(lists_data)

    new_list = {"id": new_id, "title": title, "position": new_position}

    lists_data.append(new_list)
    return new_list


@app.post("/api/cards")
async def create_card(title: str, description: Optional[str] = None, list_id: int = 1):
    """Create a new card"""
    new_id = max([c["id"] for c in cards_data], default=0) + 1

    # Get position (last in the list)
    list_cards = [c for c in cards_data if c["list_id"] == list_id]
    new_position = len(list_cards)

    new_card = {
        "id": new_id,
        "title": title,
        "description": description,
        "list_id": list_id,
        "position": new_position,
        "checklist": [],
    }

    cards_data.append(new_card)
    return new_card


@app.put("/api/cards/{card_id}/move")
async def move_card(card_id: int, new_list_id: int, new_position: int):
    """Move a card to a different list or position"""
    # Find the card
    card = next((c for c in cards_data if c["id"] == card_id), None)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    old_list_id = card["list_id"]
    old_position = card["position"]

    # Update card
    card["list_id"] = new_list_id
    card["position"] = new_position

    # Update positions of other cards in the old list
    for c in cards_data:
        if c["list_id"] == old_list_id and c["position"] > old_position:
            c["position"] -= 1

    # Update positions of other cards in the new list
    for c in cards_data:
        if (
            c["list_id"] == new_list_id
            and c["id"] != card_id
            and c["position"] >= new_position
        ):
            c["position"] += 1

    return card


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
