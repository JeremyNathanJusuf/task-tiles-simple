# Task Tiles - Trello Clone

A full-stack task management application built with FastAPI (Python) backend and React (TypeScript) frontend, featuring persistent SQLite database storage.

## Features

- 📋 **Kanban Board**: Drag and drop task cards between lists
- 🗂️ **List Management**: Create and organize task lists
- 📝 **Card Management**: Add, edit, and manage task cards
- 💾 **Persistent Storage**: SQLite database for data persistence
- 🔄 **Real-time Updates**: Live updates across the application
- 🐳 **Docker Support**: Complete containerized development environment

## Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for Python
- **SQLAlchemy**: SQL toolkit and ORM
- **SQLite**: Lightweight database
- **Alembic**: Database migrations
- **Pydantic**: Data validation using Python type hints

### Frontend
- **React**: JavaScript library for building user interfaces
- **TypeScript**: Typed superset of JavaScript
- **Axios**: HTTP client for API requests
- **CSS3**: Modern styling with Flexbox/Grid

## Development Setup

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd task-tiles-simple
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Start the development environment**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Option 2: Dev Container (VS Code)

1. **Open in VS Code**
   - Install the "Dev Containers" extension
   - Open the project in VS Code
   - Click "Reopen in Container" when prompted

2. **The dev container will automatically:**
   - Build the Docker environment
   - Install all dependencies
   - Initialize the database
   - Start the services

### Option 3: Manual Setup

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python init_db.py
python run.py
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Environment Configuration

Create a `.env` file in the project root:

```env
# Backend Configuration
DATABASE_URL=sqlite:///data/task_tiles.db
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
CHOKIDAR_USEPOLLING=true

# Development Settings
NODE_ENV=development
```

## API Endpoints

### Board Management
- `GET /api/board` - Get the main board with all lists and cards
- `POST /api/lists` - Create a new list
- `POST /api/cards` - Create a new card
- `PUT /api/cards/{card_id}/move` - Move a card to different list/position

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation.

## Database

The application uses SQLite for development with the following schema:

- **Boards**: Main board container
- **TaskLists**: Column lists within boards
- **Cards**: Individual task cards within lists

The database is automatically initialized with sample data on first run.

## Development Features

- **Hot Reload**: Both frontend and backend support hot reloading
- **Database Persistence**: Data persists between container restarts
- **Volume Mounting**: Source code is mounted for live development
- **Port Forwarding**: Automatic port forwarding in dev containers

## Project Structure

```
task-tiles-simple/
├── backend/                 # FastAPI backend
│   ├── main.py             # Main application file
│   ├── models.py           # SQLAlchemy models
│   ├── database.py         # Database configuration
│   ├── init_db.py          # Database initialization
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API services
│   │   └── types.ts        # TypeScript types
│   └── package.json        # Node.js dependencies
├── .devcontainer/          # Dev container configuration
├── docker-compose.dev.yml  # Docker Compose for development
└── README.md              # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE). 