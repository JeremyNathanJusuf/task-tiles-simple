# Task Tiles - Trello-like Task Management App

A simple, Trello-inspired task management application built with FastAPI (Python) backend and React frontend.

## Features

- **Board Management**: View your main task board immediately upon opening
- **Lists (Columns)**: Create and manage multiple lists arranged horizontally
- **Cards (Tasks)**: Add, edit, and manage individual task cards
- **Drag & Drop**: Move cards between lists and reorder within lists
- **Checklists**: Each card supports checklist functionality
- **CRUD Operations**: Full Create, Read, Update, Delete functionality

## Tech Stack

- **Backend**: FastAPI (Python 3.11)
- **Frontend**: React with TypeScript (coming soon)
- **Database**: SQLite (development), easily upgradable to PostgreSQL
- **Dev Environment**: Docker Dev Container

## Getting Started

### Prerequisites

- Docker
- VS Code with Dev Containers extension

### Setup Instructions

1. **Open in Dev Container**
   - Open this project in VS Code
   - When prompted, click "Reopen in Container" or use Command Palette: `Dev Containers: Reopen in Container`
   - The dev container will automatically build and install all dependencies

2. **Start the Backend Server**
   ```bash
   cd backend
   python run.py
   ```
   
   The API will be available at: `http://localhost:8000`
   
   - API Documentation: `http://localhost:8000/docs`
   - Alternative docs: `http://localhost:8000/redoc`

3. **Test the API**
   
   You can test the API endpoints using the interactive documentation at `/docs` or with curl:
   
   ```bash
   # Get the main board
   curl http://localhost:8000/api/board
   
   # Create a new list
   curl -X POST "http://localhost:8000/api/lists?title=New%20List"
   
   # Create a new card
   curl -X POST "http://localhost:8000/api/cards?title=New%20Task&list_id=1"
   ```

## API Endpoints

### Board Management
- `GET /api/board` - Get the main board with all lists and cards

### List Management
- `POST /api/lists` - Create a new list
  - Parameters: `title` (string)

### Card Management
- `POST /api/cards` - Create a new card
  - Parameters: `title` (string), `description` (optional), `list_id` (int)
- `PUT /api/cards/{card_id}/move` - Move a card to different list/position
  - Parameters: `new_list_id` (int), `new_position` (int)

## Project Structure

```
.
├── .devcontainer/          # Dev container configuration
│   ├── devcontainer.json   # Dev container settings
│   └── Dockerfile         # Container definition
├── backend/               # FastAPI backend
│   ├── main.py           # Main application file
│   └── run.py            # Development server script
├── frontend/             # React frontend (coming soon)
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Development

### Backend Development

The backend is built with FastAPI and includes:
- **Models**: Pydantic models for data validation
- **In-memory storage**: Simple storage for development (will be replaced with database)
- **CORS**: Configured for frontend integration
- **Auto-reload**: Development server automatically reloads on code changes

### Next Steps

1. **Database Integration**: Replace in-memory storage with SQLAlchemy + SQLite
2. **Frontend Development**: Create React frontend with drag-and-drop functionality
3. **User Authentication**: Add user management and authentication
4. **Advanced Features**: Add due dates, labels, attachments, etc.

## Contributing

1. Make sure you're working in the dev container
2. Make your changes
3. Test the API using the interactive documentation
4. Submit your changes

## License

This project is for educational purposes. 