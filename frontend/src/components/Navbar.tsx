import React, { useEffect, useState } from 'react';
import { authAPI, invitationAPI, setAuthToken } from '../services/api';
import { Invitation, UserProfile } from '../types';

interface NavbarProps {
  user: UserProfile | null;
  onLogout: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ user, onLogout }) => {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showInboxMenu, setShowInboxMenu] = useState(false);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [showAccountModal, setShowAccountModal] = useState(false);

  useEffect(() => {
    if (user) {
      loadInvitations();
    }
  }, [user]);

  const loadInvitations = async () => {
    try {
      const response = await invitationAPI.getInvitations();
      setInvitations(response.data);
    } catch (error) {
      console.error('Failed to load invitations:', error);
    }
  };

  const handleAcceptInvitation = async (invitationId: number) => {
    try {
      await invitationAPI.respondToInvitation(invitationId, { accept: true });
      loadInvitations();
      // Refresh the page to show the new board
      window.location.reload();
    } catch (error) {
      console.error('Failed to accept invitation:', error);
    }
  };

  const handleDeclineInvitation = async (invitationId: number) => {
    try {
      await invitationAPI.respondToInvitation(invitationId, { accept: false });
      loadInvitations();
    } catch (error) {
      console.error('Failed to decline invitation:', error);
    }
  };

  const handleLogout = () => {
    setAuthToken(null);
    onLogout();
  };

  const openAccountModal = () => {
    setShowAccountModal(true);
    setShowUserMenu(false);
  };

  const closeAccountModal = () => {
    setShowAccountModal(false);
  };

  const getUserInitials = (user: UserProfile): string => {
    if (user.full_name) {
      return user.full_name.split(' ').map(n => n[0]).join('').toUpperCase();
    }
    return user.username.substring(0, 2).toUpperCase();
  };

  return (
    <>
      <nav className="navbar">
        <div className="navbar-left">
          <div className="navbar-logo">
            <h1>Task Tiles</h1>
          </div>
        </div>
        
        <div className="navbar-right">
          {user && (
            <>
              {/* Account Icon */}
              <div className="navbar-icon" onClick={openAccountModal}>
                <div className="user-avatar">
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt="User Avatar" />
                  ) : (
                    <span className="user-initials">{getUserInitials(user)}</span>
                  )}
                </div>
              </div>

              {/* Inbox Icon */}
              <div className="navbar-icon" onClick={() => setShowInboxMenu(!showInboxMenu)}>
                <div className="inbox-icon">
                  <span className="inbox-symbol">📬</span>
                  {invitations.length > 0 && (
                    <span className="notification-badge">{invitations.length}</span>
                  )}
                </div>
                {showInboxMenu && (
                  <div className="dropdown-menu inbox-dropdown">
                    <div className="dropdown-header">
                      <h3>Invitations</h3>
                    </div>
                    {invitations.length === 0 ? (
                      <div className="dropdown-item">
                        <span className="no-invitations">No new invitations</span>
                      </div>
                    ) : (
                      invitations.map((invitation) => (
                        <div key={invitation.id} className="invitation-item">
                          <div className="invitation-header">
                            <strong>{invitation.inviter.username}</strong>
                            <span className="invitation-date">
                              {new Date(invitation.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="invitation-board">
                            Board: <strong>{invitation.board_title}</strong>
                          </div>
                          {invitation.message && (
                            <div className="invitation-message">
                              "{invitation.message}"
                            </div>
                          )}
                          <div className="invitation-actions">
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => handleAcceptInvitation(invitation.id)}
                            >
                              Accept
                            </button>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleDeclineInvitation(invitation.id)}
                            >
                              Decline
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* User Menu */}
              <div className="navbar-icon" onClick={() => setShowUserMenu(!showUserMenu)}>
                <div className="user-info">
                  <span className="username">{user.username}</span>
                  <span className="dropdown-arrow">▼</span>
                </div>
                {showUserMenu && (
                  <div className="dropdown-menu user-dropdown">
                    <div className="dropdown-item" onClick={openAccountModal}>
                      <span>Account Settings</span>
                    </div>
                    <div className="dropdown-item" onClick={handleLogout}>
                      <span>Logout</span>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </nav>

      {/* Account Modal */}
      {showAccountModal && (
        <AccountModal
          user={user}
          onClose={closeAccountModal}
          onUpdate={loadInvitations}
        />
      )}
    </>
  );
};

// Account Modal Component
interface AccountModalProps {
  user: UserProfile | null;
  onClose: () => void;
  onUpdate: () => void;
}

const AccountModal: React.FC<AccountModalProps> = ({ user, onClose, onUpdate }) => {
  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    avatar_url: user?.avatar_url || '',
  });
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [activeTab, setActiveTab] = useState<'profile' | 'password'>('profile');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');

    try {
      await authAPI.updateProfile(formData);
      setMessage('Profile updated successfully!');
      onUpdate();
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (error) {
      setMessage('Failed to update profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');

    if (passwordData.new_password !== passwordData.confirm_password) {
      setMessage('New passwords do not match.');
      setIsLoading(false);
      return;
    }

    try {
      await authAPI.updatePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password,
      });
      setMessage('Password updated successfully!');
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (error) {
      setMessage('Failed to update password. Please check your current password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content account-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Account Settings</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-tabs">
          <button 
            className={`tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            Profile
          </button>
          <button 
            className={`tab ${activeTab === 'password' ? 'active' : ''}`}
            onClick={() => setActiveTab('password')}
          >
            Password
          </button>
        </div>

        <div className="modal-body">
          {message && <div className="message">{message}</div>}
          
          {activeTab === 'profile' && (
            <form onSubmit={handleProfileUpdate}>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  placeholder="Enter your full name"
                />
              </div>
              
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="Enter your email"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Avatar URL</label>
                <input
                  type="url"
                  value={formData.avatar_url}
                  onChange={(e) => setFormData({ ...formData, avatar_url: e.target.value })}
                  placeholder="Enter avatar image URL"
                />
              </div>
              
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={isLoading}>
                  {isLoading ? 'Updating...' : 'Update Profile'}
                </button>
              </div>
            </form>
          )}
          
          {activeTab === 'password' && (
            <form onSubmit={handlePasswordUpdate}>
              <div className="form-group">
                <label>Current Password</label>
                <input
                  type="password"
                  value={passwordData.current_password}
                  onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                  placeholder="Enter current password"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>New Password</label>
                <input
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                  placeholder="Enter new password"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Confirm New Password</label>
                <input
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                  placeholder="Confirm new password"
                  required
                />
              </div>
              
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={isLoading}>
                  {isLoading ? 'Updating...' : 'Update Password'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default Navbar; 