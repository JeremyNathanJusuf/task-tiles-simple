import React, { useEffect, useState } from 'react';
import './App.css';
import BoardView from './components/BoardView';
import Login from './components/Login';
import Navbar from './components/Navbar';
import Register from './components/Register';
import Sidebar from './components/Sidebar';
import { authService } from './services/api';
import { User } from './types';

type AppState = 'login' | 'register' | 'authenticated';

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>('login');
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  useEffect(() => {
    // Check if user is already authenticated
    if (authService.isAuthenticated()) {
      setAppState('authenticated');
    }
  }, []);

  const handleLogin = (user: User) => {
    setCurrentUser(user);
    setAppState('authenticated');
  };

  const handleRegister = (user: User) => {
    setCurrentUser(user);
    setAppState('authenticated');
  };

  const handleLogout = () => {
    authService.removeToken();
    setCurrentUser(null);
    setAppState('login');
    setSelectedBoardId(null);
  };

  const handleSelectBoard = (boardId: number | null) => {
    setSelectedBoardId(boardId);
  };

  const renderContent = () => {
    if (appState !== 'authenticated') {
      switch (appState) {
        case 'register':
          return (
            <Register
              onRegister={handleRegister}
              onSwitchToLogin={() => setAppState('login')}
            />
          );
        default:
          return (
            <Login
              onLogin={handleLogin}
              onSwitchToRegister={() => setAppState('register')}
            />
          );
      }
    }

    return (
      <div className="app-layout">
        <Navbar user={currentUser} onLogout={handleLogout} />
        <div className="app-content">
          <Sidebar 
            selectedBoardId={selectedBoardId}
            onSelectBoard={handleSelectBoard}
          />
          <BoardView boardId={selectedBoardId} />
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      {renderContent()}
    </div>
  );
};

export default App; 