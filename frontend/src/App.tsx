import { useCallback, useEffect, useState } from 'react';
import './App.css';
import BoardView from './components/BoardView';
import Login from './components/Login';
import Navbar from './components/Navbar';
import Register from './components/Register';
import Sidebar from './components/Sidebar';
import { authAPI, boardAPI, isAuthenticated, setAuthToken } from './services/api';
import { Board, UserProfile } from './types';

function App() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [boards, setBoards] = useState<Board[]>([]);
  const [currentBoard, setCurrentBoard] = useState<Board | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState<'login' | 'register' | 'dashboard'>('login');

  const loadUserData = useCallback(async () => {
    try {
      const userResponse = await authAPI.getCurrentUser();
      setUser(userResponse.data);
      
      const boardsResponse = await boardAPI.getBoards();
      setBoards(boardsResponse.data);
      
      // Select first board by default
      if (boardsResponse.data.length > 0) {
        setCurrentBoard(boardsResponse.data[0]);
      }
      
      setCurrentView('dashboard');
    } catch (error) {
      console.error('Failed to load user data:', error);
      handleLogout();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Check if user is already authenticated
    if (isAuthenticated()) {
      loadUserData();
    } else {
      setLoading(false);
    }
  }, [loadUserData]);

  const handleLogin = async (token: string) => {
    setAuthToken(token);
    await loadUserData();
  };

  const handleLogout = () => {
    setAuthToken(null);
    setUser(null);
    setBoards([]);
    setCurrentBoard(null);
    setCurrentView('login');
  };

  const handleBoardSelect = (board: Board) => {
    setCurrentBoard(board);
  };

  const handleBoardsUpdate = async () => {
    try {
      const boardsResponse = await boardAPI.getBoards();
      setBoards(boardsResponse.data);
      
      // Update current board if it still exists
      if (currentBoard) {
        const updatedBoard = boardsResponse.data.find(b => b.id === currentBoard.id);
        if (updatedBoard) {
          setCurrentBoard(updatedBoard);
        } else {
          // Board was deleted, select first available board
          setCurrentBoard(boardsResponse.data.length > 0 ? boardsResponse.data[0] : null);
        }
      } else if (boardsResponse.data.length > 0 && !currentBoard) {
        // No board selected but boards exist, select first one
        setCurrentBoard(boardsResponse.data[0]);
      }
    } catch (error) {
      console.error('Failed to update boards:', error);
    }
  };

  const handleBoardUpdate = async () => {
    if (currentBoard) {
      try {
        const updatedBoardResponse = await boardAPI.getBoard(currentBoard.id);
        setCurrentBoard(updatedBoardResponse.data);
        
        // Also refresh the boards list to keep sidebar in sync
        const boardsResponse = await boardAPI.getBoards();
        setBoards(boardsResponse.data);
      } catch (error) {
        console.error('Failed to update board:', error);
        // Board might have been deleted, refresh boards list
        handleBoardsUpdate();
      }
    }
  };

  if (loading) {
    return (
      <div className="app">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (currentView === 'login') {
    return (
      <div className="app">
        <div className="auth-container">
          <Login 
            onLogin={handleLogin}
            onSwitchToRegister={() => setCurrentView('register')}
          />
        </div>
      </div>
    );
  }

  if (currentView === 'register') {
    return (
      <div className="app">
        <div className="auth-container">
          <Register 
            onRegister={handleLogin}
            onSwitchToLogin={() => setCurrentView('login')}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Navbar 
        user={user} 
        onLogout={handleLogout}
      />
      
      <div className="app-content">
        <Sidebar
          boards={boards}
          currentBoard={currentBoard}
          onBoardSelect={handleBoardSelect}
          onBoardsUpdate={handleBoardsUpdate}
          user={user}
        />
        
        <div className="main-content">
          {currentBoard ? (
            <BoardView
              board={currentBoard}
              onBoardUpdate={handleBoardUpdate}
              user={user}
            />
          ) : (
            <div className="empty-state">
              <div className="empty-state-content">
                <h2>Welcome to Task Tiles!</h2>
                <p>Create your first board to get started with organizing your tasks.</p>
                <div className="welcome-features">
                  <div className="feature">
                    <span className="feature-icon">👥</span>
                    <h3>Collaborate</h3>
                    <p>Invite team members to work together on shared boards</p>
                  </div>
                  <div className="feature">
                    <span className="feature-icon">📋</span>
                    <h3>Organize</h3>
                    <p>Create lists and cards to organize your tasks</p>
                  </div>
                  <div className="feature">
                    <span className="feature-icon">✅</span>
                    <h3>Track Progress</h3>
                    <p>Use checklists and move cards to track your progress</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App; 