#!/usr/bin/env python3
"""
Database initialization script for Task Tiles
This script creates the database tables and optionally populates them with sample data.
"""
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_database, get_db_context
from models import Base, User, Board, TaskList, Card
from auth import get_password_hash


def create_sample_data():
    """Create sample data for the application"""
    with get_db_context() as db:
        # Check if users already exist
        existing_user = db.query(User).first()
        if existing_user:
            print("Sample data already exists. Skipping creation.")
            return
        
        # Create sample users
        demo_user = User(
            username="demo",
            email="demo@example.com",
            hashed_password=get_password_hash("demo123")
        )
        
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123")
        )
        
        db.add_all([demo_user, admin_user])
        db.flush()  # Flush to get the IDs
        
        # Create sample boards for demo user
        personal_board = Board(
            title="Personal Tasks",
            description="My personal task management board",
            owner_id=demo_user.id
        )
        
        work_board = Board(
            title="Work Projects",
            description="Professional work tracking",
            owner_id=demo_user.id
        )
        
        db.add_all([personal_board, work_board])
        db.flush()
        
        # Create sample lists for personal board
        personal_lists = [
            TaskList(title="To Do", position=0, board_id=personal_board.id),
            TaskList(title="In Progress", position=1, board_id=personal_board.id),
            TaskList(title="Done", position=2, board_id=personal_board.id)
        ]
        
        # Create sample lists for work board
        work_lists = [
            TaskList(title="Backlog", position=0, board_id=work_board.id),
            TaskList(title="Sprint Planning", position=1, board_id=work_board.id),
            TaskList(title="Development", position=2, board_id=work_board.id),
            TaskList(title="Testing", position=3, board_id=work_board.id),
            TaskList(title="Completed", position=4, board_id=work_board.id)
        ]
        
        db.add_all(personal_lists + work_lists)
        db.flush()
        
        # Create sample cards for personal board
        personal_cards = [
            Card(
                title="Buy groceries",
                description="Get milk, bread, and eggs",
                list_id=personal_lists[0].id,  # To Do
                position=0,
                checklist=["Milk", "Bread", "Eggs"]
            ),
            Card(
                title="Plan weekend trip",
                description="Research destinations and book hotel",
                list_id=personal_lists[0].id,  # To Do
                position=1,
                checklist=["Research destinations", "Compare prices", "Book hotel", "Pack bags"]
            ),
            Card(
                title="Learn FastAPI",
                description="Complete online course",
                list_id=personal_lists[1].id,  # In Progress
                position=0,
                checklist=["Watch introduction videos", "Build sample project", "Read documentation"]
            ),
            Card(
                title="Exercise routine",
                description="Daily morning workout",
                list_id=personal_lists[2].id,  # Done
                position=0,
                checklist=["Monday workout", "Wednesday workout", "Friday workout"]
            )
        ]
        
        # Create sample cards for work board
        work_cards = [
            Card(
                title="User Authentication System",
                description="Implement JWT-based authentication",
                list_id=work_lists[0].id,  # Backlog
                position=0,
                checklist=["Design user model", "Create login endpoint", "Add JWT middleware", "Test authentication"]
            ),
            Card(
                title="Board Management API",
                description="Create, read, update, delete boards",
                list_id=work_lists[1].id,  # Sprint Planning
                position=0,
                checklist=["Design board schema", "Create CRUD endpoints", "Add user authorization", "Write tests"]
            ),
            Card(
                title="Drag & Drop Feature",
                description="Implement card drag and drop functionality",
                list_id=work_lists[2].id,  # Development
                position=0,
                checklist=["Frontend drag implementation", "Backend move endpoint", "Position updates", "UI feedback"]
            ),
            Card(
                title="Database Setup",
                description="Configure PostgreSQL database",
                list_id=work_lists[4].id,  # Completed
                position=0,
                checklist=["Install PostgreSQL", "Create database", "Run migrations", "Test connection"]
            )
        ]
        
        db.add_all(personal_cards + work_cards)
        db.commit()
        
        print("Sample data created successfully!")
        print(f"Created users: {demo_user.username}, {admin_user.username}")
        print(f"Created boards: {personal_board.title}, {work_board.title}")
        print(f"Created lists: {len(personal_lists) + len(work_lists)} total")
        print(f"Created cards: {len(personal_cards) + len(work_cards)} total")
        print("\nDemo credentials:")
        print("Username: demo, Password: demo123")
        print("Username: admin, Password: admin123")


def main():
    """Main function to initialize the database"""
    print("Initializing Task Tiles database...")
    
    try:
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Remove old database file for clean start
        db_file = os.path.join(data_dir, 'task_tiles.db')
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"Removed old database file: {db_file}")
        
        # Create tables
        init_database()
        
        # Create sample data
        create_sample_data()
        
        print("\nDatabase initialization completed successfully!")
        print("You can now start the server and login with the demo credentials.")
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 