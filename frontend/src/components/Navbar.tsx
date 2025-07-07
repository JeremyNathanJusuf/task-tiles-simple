import { LogOut, User } from 'lucide-react';
import React from 'react';
import { User as UserType } from '../types';

interface NavbarProps {
  user: UserType | null;
  onLogout: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ user, onLogout }) => {
  return (
    <nav className="navbar">
      <div className="navbar-left">
        <div className="app-logo">
          <span className="logo-icon">📋</span>
          <span className="logo-text">Task Tiles</span>
        </div>
      </div>
      
      <div className="navbar-right">
        {user && (
          <div className="user-menu">
            <div className="user-info">
              <User size={20} />
              <span>{user.username}</span>
            </div>
            <button onClick={onLogout} className="logout-button">
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar; 