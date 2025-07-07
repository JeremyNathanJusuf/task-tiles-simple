#!/usr/bin/env python3
"""
Database initialization script for Task Tiles
This script creates the database tables and populates them with sample data.
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_database, get_db_context
from models import Base, Board, TaskList, Card


def create_sample_data():
    """Create sample data for the application"""
    with get_db_context() as db:
        # Check if data already exists
        existing_board = db.query(Board).first()
        if existing_board:
            print("Sample data already exists. Skipping creation.")
            return
        
        # Create sample board
        board = Board(id=1, title="My Task Board")
        db.add(board)
        db.flush()  # Flush to get the ID
        
        # Create sample lists
        todo_list = TaskList(id=1, title="To Do", position=0, board_id=board.id)
        in_progress_list = TaskList(id=2, title="In Progress", position=1, board_id=board.id)
        done_list = TaskList(id=3, title="Done", position=2, board_id=board.id)
        
        db.add_all([todo_list, in_progress_list, done_list])
        db.flush()  # Flush to get the IDs
        
        # Create sample cards
        cards = [
            Card(
                id=1,
                title="Design wireframes",
                description="Create wireframes for the main interface",
                list_id=todo_list.id,
                position=0,
                checklist=[]
            ),
            Card(
                id=2,
                title="Setup backend",
                description="Initialize FastAPI project",
                list_id=in_progress_list.id,
                position=0,
                checklist=[]
            ),
            Card(
                id=3,
                title="Create logo",
                description="Design company logo",
                list_id=done_list.id,
                position=0,
                checklist=[]
            ),
        ]
        
        db.add_all(cards)
        db.commit()
        
        print("Sample data created successfully!")
        print(f"Created board: {board.title}")
        print(f"Created {len([todo_list, in_progress_list, done_list])} lists")
        print(f"Created {len(cards)} cards")


def main():
    """Main function to initialize the database"""
    print("Initializing Task Tiles database...")
    
    try:
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Create tables
        init_database()
        
        # Create sample data
        create_sample_data()
        
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 