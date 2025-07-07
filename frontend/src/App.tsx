import { useCallback, useEffect, useState } from 'react';
import './App.css';
import BoardView from './components/BoardView';
import Chatbot from './components/Chatbot';
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
  const [isUpdating, setIsUpdating] = useState(false);

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

  const refreshBoardData = useCallback(async () => {
    if (currentView !== 'dashboard' || !user || isUpdating) return;

    try {
      const boardsResponse = await boardAPI.getBoards();
      
      setBoards(prevBoards => {
        const newBoards = boardsResponse.data;
        
        // If we have a new board (invitation accepted), show notification
        if (newBoards.length > prevBoards.length) {
          console.log('New board detected - invitation likely accepted');
        }
        
        return newBoards;
      });
      
      // Update current board if it still exists
      setCurrentBoard(prevCurrentBoard => {
        if (prevCurrentBoard) {
          const updatedBoard = boardsResponse.data.find(b => b.id === prevCurrentBoard.id);
          if (updatedBoard) {
            // Check if board has new activity (more members, etc.)
            const memberCountChanged = updatedBoard.members.length !== prevCurrentBoard.members.length;
            if (memberCountChanged) {
              console.log('Board membership changed - refreshing board view');
            }
            return updatedBoard;
          } else {
            // Board was deleted, select first available board
            return boardsResponse.data.length > 0 ? boardsResponse.data[0] : null;
          }
        } else if (boardsResponse.data.length > 0) {
          // No board selected but boards exist, select first one
          return boardsResponse.data[0];
        }
        return prevCurrentBoard;
      });
    } catch (error) {
      console.error('Failed to refresh board data:', error);
    }
  }, [currentView, user, isUpdating]);

  useEffect(() => {
    // Check if user is already authenticated
    if (isAuthenticated()) {
      loadUserData();
    } else {
      setLoading(false);
    }
  }, [loadUserData]);

  // Set up polling for real-time board updates
  useEffect(() => {
    if (currentView === 'dashboard' && user) {
      // Poll every 45 seconds for board updates
      const pollInterval = setInterval(() => {
        refreshBoardData();
      }, 45000);

      return () => clearInterval(pollInterval);
    }
  }, [currentView, user, refreshBoardData]);

  // Refresh when window gains focus
  useEffect(() => {
    const handleWindowFocus = () => {
      if (currentView === 'dashboard' && user) {
        refreshBoardData();
      }
    };

    window.addEventListener('focus', handleWindowFocus);
    return () => window.removeEventListener('focus', handleWindowFocus);
  }, [currentView, user, refreshBoardData]);

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
    // Prevent multiple simultaneous updates
    if (isUpdating) return;
    
    setIsUpdating(true);
    try {
      const boardsResponse = await boardAPI.getBoards();
      setBoards(boardsResponse.data);
      
      // Update current board if it still exists
      setCurrentBoard(prevCurrentBoard => {
        if (prevCurrentBoard) {
          const updatedBoard = boardsResponse.data.find(b => b.id === prevCurrentBoard.id);
          if (updatedBoard) {
            return updatedBoard;
          } else {
            // Board was deleted, select first available board
            return boardsResponse.data.length > 0 ? boardsResponse.data[0] : null;
          }
        } else if (boardsResponse.data.length > 0) {
          // No board selected but boards exist, select first one
          return boardsResponse.data[0];
        }
        return prevCurrentBoard;
      });
    } catch (error) {
      console.error('Failed to update boards:', error);
    } finally {
      setIsUpdating(false);
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

  // Handle board selection by ID (for chatbot callbacks)
  const handleBoardSelectById = (boardId: number) => {
    const board = boards.find(b => b.id === boardId);
    if (board) {
      handleBoardSelect(board);
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
        
        <main className="main-content">
          {currentBoard ? (
            <BoardView
              board={currentBoard}
              onBoardUpdate={handleBoardsUpdate}
              user={user}
            />
          ) : (
            <div className="empty-state">
              <div className="empty-state-content">
                <h2>Welcome to Task Tiles!</h2>
                <p>Your intelligent Kanban board with AI-powered task management</p>
                
                <div className="welcome-features">
                  <div className="feature">
                    <span className="feature-icon">📋</span>
                    <h3>Smart Boards</h3>
                    <p>Organize your projects with customizable boards and lists</p>
                  </div>
                  <div className="feature">
                    <span className="feature-icon">🤖</span>
                    <h3>AI Assistant</h3>
                    <p>Chat with our AI to create tasks, move cards, and manage your workflow</p>
                  </div>
                  <div className="feature">
                    <span className="feature-icon">👥</span>
                    <h3>Team Collaboration</h3>
                    <p>Invite team members to collaborate on shared boards</p>
                  </div>
                  <div className="feature">
                    <span className="feature-icon">🎯</span>
                    <h3>Priority Management</h3>
                    <p>Set priorities and track progress with visual indicators</p>
                  </div>
                </div>
                
                <div className="welcome-actions">
                  <p>To get started, select a board from the sidebar or create a new one.</p>
                  {boards.length === 0 && (
                    <p><strong>You don't have any boards yet!</strong> Click the "+ New Board" button to create your first board.</p>
                  )}
                </div>
                
                <div className="welcome-stats">
                  <div className="stat">
                    <span className="stat-number">{boards.length}</span>
                    <span className="stat-label">Board{boards.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-number">{boards.reduce((total, board) => total + board.lists.reduce((listTotal, list) => listTotal + list.cards.length, 0), 0)}</span>
                    <span className="stat-label">Total Tasks</span>
                  </div>
                  <div className="stat">
                    <span className="stat-number">{boards.reduce((total, board) => total + (board.is_shared ? board.members.length + 1 : 1), 0)}</span>
                    <span className="stat-label">Team Members</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
        
        {/* Add Chatbot with callback functions for immediate updates */}
        <Chatbot 
          user={user} 
          currentBoard={currentBoard}
          onBoardsUpdate={handleBoardsUpdate}
          onBoardChange={handleBoardSelectById}
        />
      </div>
    </div>
  );
}

export default App; 