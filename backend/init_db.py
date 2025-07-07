#!/usr/bin/env python3
"""
Database initialization script for Task Tiles with collaborative features
This script creates the database tables without any sample data for a clean start.
"""
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, create_tables, Base, engine
from models import (
    User,
    Board,
    TaskList,
    Card,
    BoardMember,
    Invitation,
    CardContributor,
    InvitationStatus,
    BoardRole,
)
from auth import get_password_hash


def init_clean_database():
    """Initialize the database with clean tables (no sample data)"""
    print("Initializing clean database...")

    # Create all tables
    Base.metadata.drop_all(bind=engine)
    create_tables()

    print("Database initialized successfully!")
    print("Empty database is ready for use.")
    print("\nYou can now:")
    print("1. Start the backend server: python main.py")
    print("2. Register a new account through the frontend")
    print("3. Begin creating your boards and collaborating!")


def init_database_with_sample_data():
    """Initialize the database with sample data for demonstration"""
    print("Initializing database with sample data...")

    # Create all tables
    Base.metadata.drop_all(bind=engine)
    create_tables()

    # Create a database session
    db = SessionLocal()

    try:
        # Create sample users
        print("Creating sample users...")

        # Demo user
        demo_user = User(
            username="demo",
            email="demo@example.com",
            full_name="Demo User",
            avatar_url="https://i.pravatar.cc/150?img=1",
            hashed_password=get_password_hash("demo123"),
        )
        db.add(demo_user)

        # Admin user
        admin_user = User(
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            avatar_url="https://i.pravatar.cc/150?img=2",
            hashed_password=get_password_hash("admin123"),
        )
        db.add(admin_user)

        # Additional sample users
        alice_user = User(
            username="alice",
            email="alice@example.com",
            full_name="Alice Johnson",
            avatar_url="https://i.pravatar.cc/150?img=3",
            hashed_password=get_password_hash("alice123"),
        )
        db.add(alice_user)

        bob_user = User(
            username="bob",
            email="bob@example.com",
            full_name="Bob Smith",
            avatar_url="https://i.pravatar.cc/150?img=4",
            hashed_password=get_password_hash("bob123"),
        )
        db.add(bob_user)

        charlie_user = User(
            username="charlie",
            email="charlie@example.com",
            full_name="Charlie Brown",
            avatar_url="https://i.pravatar.cc/150?img=5",
            hashed_password=get_password_hash("charlie123"),
        )
        db.add(charlie_user)

        # Commit users first to get their IDs
        db.commit()
        db.refresh(demo_user)
        db.refresh(admin_user)
        db.refresh(alice_user)
        db.refresh(bob_user)
        db.refresh(charlie_user)

        print("Creating sample boards...")

        # Demo user's personal board
        demo_board = Board(
            title="Demo's Personal Board",
            description="A personal Kanban board for demo purposes",
            owner_id=demo_user.id,
        )
        db.add(demo_board)

        # Admin user's project board
        admin_board = Board(
            title="Admin's Project Board",
            description="Project management board for admin tasks",
            owner_id=admin_user.id,
        )
        db.add(admin_board)

        # Alice's collaborative board
        alice_board = Board(
            title="Team Collaboration Board",
            description="A shared board for team collaboration",
            owner_id=alice_user.id,
        )
        db.add(alice_board)

        # Bob's development board
        bob_board = Board(
            title="Development Sprint Board",
            description="Sprint planning and development tracking",
            owner_id=bob_user.id,
        )
        db.add(bob_board)

        # Commit boards to get their IDs
        db.commit()
        db.refresh(demo_board)
        db.refresh(admin_board)
        db.refresh(alice_board)
        db.refresh(bob_board)

        print("Creating board memberships...")

        # Make demo user a member of Alice's board
        alice_board_member1 = BoardMember(
            board_id=alice_board.id, user_id=demo_user.id, role=BoardRole.MEMBER
        )
        db.add(alice_board_member1)

        # Make Charlie a member of Alice's board
        alice_board_member2 = BoardMember(
            board_id=alice_board.id, user_id=charlie_user.id, role=BoardRole.MEMBER
        )
        db.add(alice_board_member2)

        # Make Alice a member of Bob's board
        bob_board_member1 = BoardMember(
            board_id=bob_board.id, user_id=alice_user.id, role=BoardRole.MEMBER
        )
        db.add(bob_board_member1)

        db.commit()

        print("Creating sample invitations...")

        # Pending invitation from Admin to Bob
        pending_invitation = Invitation(
            board_id=admin_board.id,
            inviter_id=admin_user.id,
            invitee_id=bob_user.id,
            message="Join our project board to help with administrative tasks!",
            status=InvitationStatus.PENDING,
        )
        db.add(pending_invitation)

        # Another pending invitation from Charlie to Demo
        pending_invitation2 = Invitation(
            board_id=alice_board.id,
            inviter_id=charlie_user.id,
            invitee_id=admin_user.id,
            message="Would you like to join our collaborative team board?",
            status=InvitationStatus.PENDING,
        )
        db.add(pending_invitation2)

        db.commit()

        print("Creating sample lists...")

        # Lists for Demo's board
        demo_todo_list = TaskList(title="To Do", position=0, board_id=demo_board.id)
        demo_progress_list = TaskList(
            title="In Progress", position=1, board_id=demo_board.id
        )
        demo_done_list = TaskList(title="Done", position=2, board_id=demo_board.id)

        db.add_all([demo_todo_list, demo_progress_list, demo_done_list])

        # Lists for Admin's board
        admin_backlog_list = TaskList(
            title="Backlog", position=0, board_id=admin_board.id
        )
        admin_active_list = TaskList(
            title="Active", position=1, board_id=admin_board.id
        )
        admin_review_list = TaskList(
            title="Review", position=2, board_id=admin_board.id
        )
        admin_complete_list = TaskList(
            title="Complete", position=3, board_id=admin_board.id
        )

        db.add_all(
            [
                admin_backlog_list,
                admin_active_list,
                admin_review_list,
                admin_complete_list,
            ]
        )

        # Lists for Alice's collaborative board
        alice_ideas_list = TaskList(title="Ideas", position=0, board_id=alice_board.id)
        alice_planning_list = TaskList(
            title="Planning", position=1, board_id=alice_board.id
        )
        alice_working_list = TaskList(
            title="Working", position=2, board_id=alice_board.id
        )
        alice_testing_list = TaskList(
            title="Testing", position=3, board_id=alice_board.id
        )
        alice_finished_list = TaskList(
            title="Finished", position=4, board_id=alice_board.id
        )

        db.add_all(
            [
                alice_ideas_list,
                alice_planning_list,
                alice_working_list,
                alice_testing_list,
                alice_finished_list,
            ]
        )

        # Lists for Bob's development board
        bob_todo_list = TaskList(
            title="Sprint Backlog", position=0, board_id=bob_board.id
        )
        bob_progress_list = TaskList(
            title="In Development", position=1, board_id=bob_board.id
        )
        bob_testing_list = TaskList(title="Testing", position=2, board_id=bob_board.id)
        bob_done_list = TaskList(title="Done", position=3, board_id=bob_board.id)

        db.add_all([bob_todo_list, bob_progress_list, bob_testing_list, bob_done_list])

        # Commit lists to get their IDs
        db.commit()
        db.refresh(demo_todo_list)
        db.refresh(demo_progress_list)
        db.refresh(demo_done_list)
        db.refresh(admin_backlog_list)
        db.refresh(admin_active_list)
        db.refresh(admin_review_list)
        db.refresh(admin_complete_list)
        db.refresh(alice_ideas_list)
        db.refresh(alice_planning_list)
        db.refresh(alice_working_list)
        db.refresh(alice_testing_list)
        db.refresh(alice_finished_list)
        db.refresh(bob_todo_list)
        db.refresh(bob_progress_list)
        db.refresh(bob_testing_list)
        db.refresh(bob_done_list)

        print("Creating sample cards...")

        # Demo board cards
        demo_card1 = Card(
            title="Welcome to Task Tiles!",
            description="This is your first card. You can edit it, move it, or delete it.",
            list_id=demo_todo_list.id,
            position=0,
            created_by=demo_user.id,
            checklist=[
                "Read the documentation",
                "Explore the interface",
                "Create your first board",
            ],
        )

        demo_card2 = Card(
            title="Try the drag and drop feature",
            description="Drag this card to different lists to see how it works.",
            list_id=demo_progress_list.id,
            position=0,
            created_by=demo_user.id,
            checklist=["Move card between lists", "Reorder cards within a list"],
        )

        demo_card3 = Card(
            title="Invite team members",
            description="Share your boards with colleagues for collaboration.",
            list_id=demo_done_list.id,
            position=0,
            created_by=demo_user.id,
            checklist=[
                "Find the invite button",
                "Add team member usernames",
                "Send invitations",
            ],
        )

        db.add_all([demo_card1, demo_card2, demo_card3])

        # Admin board cards
        admin_card1 = Card(
            title="Review user feedback",
            description="Analyze user feedback and prioritize improvements.",
            list_id=admin_backlog_list.id,
            position=0,
            created_by=admin_user.id,
            checklist=[
                "Collect feedback",
                "Analyze patterns",
                "Create improvement tickets",
            ],
        )

        admin_card2 = Card(
            title="Update system documentation",
            description="Keep the system documentation up to date.",
            list_id=admin_active_list.id,
            position=0,
            created_by=admin_user.id,
            checklist=[
                "Review current docs",
                "Update API documentation",
                "Add new features",
            ],
        )

        admin_card3 = Card(
            title="Security audit",
            description="Conduct regular security audits.",
            list_id=admin_review_list.id,
            position=0,
            created_by=admin_user.id,
            checklist=[
                "Run security scan",
                "Review access controls",
                "Update security policies",
            ],
        )

        db.add_all([admin_card1, admin_card2, admin_card3])

        # Alice's collaborative board cards
        alice_card1 = Card(
            title="Brainstorm new features",
            description="Collaborative brainstorming session for new app features.",
            list_id=alice_ideas_list.id,
            position=0,
            created_by=alice_user.id,
            checklist=[
                "Schedule brainstorming session",
                "Invite all team members",
                "Document ideas",
            ],
        )

        alice_card2 = Card(
            title="Design user interface mockups",
            description="Create mockups for the new collaboration features.",
            list_id=alice_planning_list.id,
            position=0,
            created_by=alice_user.id,
            checklist=[
                "Create wireframes",
                "Design UI components",
                "Get team feedback",
            ],
        )

        alice_card3 = Card(
            title="Implement real-time collaboration",
            description="Add real-time updates for collaborative editing.",
            list_id=alice_working_list.id,
            position=0,
            created_by=alice_user.id,
            checklist=[
                "Set up WebSocket connection",
                "Implement live updates",
                "Test with multiple users",
            ],
        )

        alice_card4 = Card(
            title="User avatar system",
            description="Implement user avatars and profile pictures.",
            list_id=alice_testing_list.id,
            position=0,
            created_by=alice_user.id,
            checklist=[
                "Upload avatar functionality",
                "Display avatars on cards",
                "Profile page integration",
            ],
        )

        db.add_all([alice_card1, alice_card2, alice_card3, alice_card4])

        # Bob's development board cards
        bob_card1 = Card(
            title="Set up development environment",
            description="Configure local development environment for new team members.",
            list_id=bob_todo_list.id,
            position=0,
            created_by=bob_user.id,
            checklist=["Install dependencies", "Configure database", "Set up Docker"],
        )

        bob_card2 = Card(
            title="API endpoint optimization",
            description="Optimize slow API endpoints for better performance.",
            list_id=bob_progress_list.id,
            position=0,
            created_by=bob_user.id,
            checklist=[
                "Identify slow endpoints",
                "Add database indexes",
                "Implement caching",
            ],
        )

        bob_card3 = Card(
            title="Unit test coverage",
            description="Improve unit test coverage for critical components.",
            list_id=bob_testing_list.id,
            position=0,
            created_by=bob_user.id,
            checklist=["Write API tests", "Add frontend tests", "Achieve 80% coverage"],
        )

        db.add_all([bob_card1, bob_card2, bob_card3])

        # Commit cards to get their IDs
        db.commit()
        db.refresh(demo_card1)
        db.refresh(demo_card2)
        db.refresh(demo_card3)
        db.refresh(alice_card1)
        db.refresh(alice_card2)
        db.refresh(alice_card3)
        db.refresh(alice_card4)
        db.refresh(bob_card1)
        db.refresh(bob_card2)
        db.refresh(bob_card3)

        print("Creating card contributors...")

        # Add contributors to demonstrate collaborative features
        # Demo user contributed to Alice's card
        contrib1 = CardContributor(card_id=alice_card2.id, user_id=demo_user.id)
        db.add(contrib1)

        # Charlie contributed to Alice's card
        contrib2 = CardContributor(card_id=alice_card2.id, user_id=charlie_user.id)
        db.add(contrib2)

        # Alice contributed to Alice's card (creator)
        contrib3 = CardContributor(card_id=alice_card2.id, user_id=alice_user.id)
        db.add(contrib3)

        # Demo user contributed to Alice's testing card
        contrib4 = CardContributor(card_id=alice_card4.id, user_id=demo_user.id)
        db.add(contrib4)

        # Alice contributed to Alice's testing card (creator)
        contrib5 = CardContributor(card_id=alice_card4.id, user_id=alice_user.id)
        db.add(contrib5)

        # Alice contributed to Bob's card
        contrib6 = CardContributor(card_id=bob_card2.id, user_id=alice_user.id)
        db.add(contrib6)

        # Bob contributed to Bob's card (creator)
        contrib7 = CardContributor(card_id=bob_card2.id, user_id=bob_user.id)
        db.add(contrib7)

        # Add all original creators as contributors
        contrib8 = CardContributor(card_id=demo_card1.id, user_id=demo_user.id)
        contrib9 = CardContributor(card_id=demo_card2.id, user_id=demo_user.id)
        contrib10 = CardContributor(card_id=demo_card3.id, user_id=demo_user.id)
        contrib11 = CardContributor(card_id=admin_card1.id, user_id=admin_user.id)
        contrib12 = CardContributor(card_id=admin_card2.id, user_id=admin_user.id)
        contrib13 = CardContributor(card_id=admin_card3.id, user_id=admin_user.id)
        contrib14 = CardContributor(card_id=alice_card1.id, user_id=alice_user.id)
        contrib15 = CardContributor(card_id=alice_card3.id, user_id=alice_user.id)
        contrib16 = CardContributor(card_id=bob_card1.id, user_id=bob_user.id)
        contrib17 = CardContributor(card_id=bob_card3.id, user_id=bob_user.id)

        db.add_all(
            [
                contrib8,
                contrib9,
                contrib10,
                contrib11,
                contrib12,
                contrib13,
                contrib14,
                contrib15,
                contrib16,
                contrib17,
            ]
        )

        # Commit all changes
        db.commit()

        print("Database initialized successfully!")
        print("\nSample users created:")
        print("- demo / demo123 (Demo User)")
        print("- admin / admin123 (Admin User)")
        print("- alice / alice123 (Alice Johnson)")
        print("- bob / bob123 (Bob Smith)")
        print("- charlie / charlie123 (Charlie Brown)")
        print("\nFeatures demonstrated:")
        print("- Personal and shared boards")
        print("- Board invitations and memberships")
        print("- User avatars and profiles")
        print("- Card contributors and collaboration")
        print("- Pending invitations for testing")

    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        init_database_with_sample_data()
    else:
        init_clean_database()
