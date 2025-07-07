import React, { useCallback, useEffect, useState } from 'react';
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

  const loadInvitations = useCallback(async () => {
    if (!user) return;
    
    try {
      const response = await invitationAPI.getInvitations();
      setInvitations(response.data);
    } catch (error) {
      console.error('Failed to load invitations:', error);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      loadInvitations();
      
      // Set up polling for real-time updates every 30 seconds
      const pollInterval = setInterval(() => {
        loadInvitations();
      }, 30000);

      // Cleanup interval on unmount
      return () => clearInterval(pollInterval);
    }
  }, [user, loadInvitations]);

  // Also check for updates when user becomes active (focuses window)
  useEffect(() => {
    const handleWindowFocus = () => {
      if (user) {
        loadInvitations();
      }
    };

    window.addEventListener('focus', handleWindowFocus);
    return () => window.removeEventListener('focus', handleWindowFocus);
  }, [user, loadInvitations]);

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
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // For now, we'll just create a data URL for preview
      // In a real app, you'd upload to a cloud service and get a URL
      const reader = new FileReader();
      reader.onload = (event) => {
        const result = event.target?.result as string;
        setFormData({ ...formData, avatar_url: result });
      };
      reader.readAsDataURL(file);
    }
  };

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage('');

    try {
      await authAPI.updateProfile(formData);
      setMessage('Profile updated successfully!');
      setMessageType('success');
      onUpdate();
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (error) {
      setMessage('Failed to update profile. Please try again.');
      setMessageType('error');
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
      setMessageType('error');
      setIsLoading(false);
      return;
    }

    try {
      await authAPI.updatePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password,
      });
      setMessage('Password updated successfully!');
      setMessageType('success');
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (error) {
      setMessage('Failed to update password. Please check your current password.');
      setMessageType('error');
    } finally {
      setIsLoading(false);
    }
  };

  const getUserInitials = (username: string, fullName?: string): string => {
    if (fullName) {
      return fullName.split(' ').map(n => n[0]).join('').toUpperCase();
    }
    return username.substring(0, 2).toUpperCase();
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
          {message && (
            <div className={`message ${messageType}`}>
              {message}
            </div>
          )}
          
          {activeTab === 'profile' && (
            <form onSubmit={handleProfileUpdate}>
              <div className="form-group">
                <label>Avatar</label>
                <div className="avatar-upload-section">
                  <div className="avatar-preview">
                    {formData.avatar_url ? (
                      <img src={formData.avatar_url} alt="Avatar preview" />
                    ) : (
                      <span className="avatar-initials">
                        {getUserInitials(user?.username || '', formData.full_name)}
                      </span>
                    )}
                  </div>
                  <div className="avatar-upload-controls">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileUpload}
                      id="avatar-upload"
                      style={{ display: 'none' }}
                    />
                    <label htmlFor="avatar-upload" className="btn btn-secondary btn-sm">
                      Upload Image
                    </label>
                    <span className="upload-hint">Or enter URL below</span>
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label>Avatar URL</label>
                <input
                  type="url"
                  value={formData.avatar_url}
                  onChange={(e) => setFormData({ ...formData, avatar_url: e.target.value })}
                  placeholder="https://example.com/avatar.jpg"
                />
              </div>
              
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
                  placeholder="your.email@example.com"
                  required
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
                  placeholder="Enter your current password"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>New Password</label>
                <input
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                  placeholder="Enter a new password"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>Confirm New Password</label>
                <input
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                  placeholder="Confirm your new password"
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