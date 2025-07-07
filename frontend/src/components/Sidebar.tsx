import React, { useState } from 'react';
import { boardAPI } from '../services/api';
import { Board, BoardCreate, BoardInvite, UserProfile } from '../types';

interface SidebarProps {
  boards: Board[];
  currentBoard: Board | null;
  onBoardSelect: (board: Board) => void;
  onBoardsUpdate: () => void;
  user: UserProfile | null;
}

const Sidebar: React.FC<SidebarProps> = ({ 
  boards, 
  currentBoard, 
  onBoardSelect, 
  onBoardsUpdate,
  user 
}) => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [selectedBoardForInvite, setSelectedBoardForInvite] = useState<Board | null>(null);
  const [newBoardTitle, setNewBoardTitle] = useState('');
  const [newBoardDescription, setNewBoardDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateBoard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBoardTitle.trim()) return;

    setIsCreating(true);
    try {
      const boardData: BoardCreate = {
        title: newBoardTitle.trim(),
        description: newBoardDescription.trim() || undefined,
      };
      
      await boardAPI.createBoard(boardData);
      setNewBoardTitle('');
      setNewBoardDescription('');
      setShowCreateForm(false);
      onBoardsUpdate();
    } catch (error) {
      console.error('Failed to create board:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteBoard = async (boardId: number, boardTitle: string) => {
    if (window.confirm(`Are you sure you want to delete "${boardTitle}"?`)) {
      try {
        await boardAPI.deleteBoard(boardId);
        onBoardsUpdate();
      } catch (error) {
        console.error('Failed to delete board:', error);
      }
    }
  };

  const openInviteModal = (board: Board) => {
    setSelectedBoardForInvite(board);
    setShowInviteModal(true);
  };

  const closeInviteModal = () => {
    setSelectedBoardForInvite(null);
    setShowInviteModal(false);
  };

  const isOwner = (board: Board): boolean => {
    return user?.id === board.owner.id;
  };

  const getBoardTypeLabel = (board: Board): string => {
    if (isOwner(board)) {
      return board.is_shared ? 'Shared' : 'Personal';
    } else {
      return 'Member';
    }
  };

  return (
    <>
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>Your Boards</h2>
          <button 
            className="btn btn-primary btn-sm"
            onClick={() => setShowCreateForm(true)}
          >
            + New Board
          </button>
        </div>

        <div className="boards-list">
          {boards.map((board) => (
            <div key={board.id} className={`board-item ${currentBoard?.id === board.id ? 'active' : ''}`}>
              <div className="board-main" onClick={() => onBoardSelect(board)}>
                <h3 className="board-title">{board.title}</h3>
                <div className="board-meta">
                  <span className={`board-type ${getBoardTypeLabel(board).toLowerCase()}`}>
                    {getBoardTypeLabel(board)}
                  </span>
                  <span className="board-owner">
                    {isOwner(board) ? 'You' : board.owner.username}
                  </span>
                </div>
                {board.is_shared && (
                  <div className="board-members">
                    <span className="members-count">
                      {board.members.length + 1} member{board.members.length === 0 ? '' : 's'}
                    </span>
                  </div>
                )}
              </div>
              
              <div className="board-actions">
                {isOwner(board) && (
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      openInviteModal(board);
                    }}
                    title="Invite users"
                  >
                    👥
                  </button>
                )}
                {isOwner(board) && (
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteBoard(board.id, board.title);
                    }}
                    title="Delete board"
                  >
                    🗑️
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {showCreateForm && (
          <div className="create-board-form">
            <h3>Create New Board</h3>
            <form onSubmit={handleCreateBoard}>
              <div className="form-group">
                <input
                  type="text"
                  value={newBoardTitle}
                  onChange={(e) => setNewBoardTitle(e.target.value)}
                  placeholder="Board title"
                  required
                  autoFocus
                />
              </div>
              <div className="form-group">
                <textarea
                  value={newBoardDescription}
                  onChange={(e) => setNewBoardDescription(e.target.value)}
                  placeholder="Board description (optional)"
                  rows={3}
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={isCreating}>
                  {isCreating ? 'Creating...' : 'Create Board'}
                </button>
                <button 
                  type="button" 
                  className="btn btn-secondary"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
      </div>

      {/* Invite Modal */}
      {showInviteModal && selectedBoardForInvite && (
        <InviteModal
          board={selectedBoardForInvite}
          onClose={closeInviteModal}
          onInviteSent={onBoardsUpdate}
        />
      )}
    </>
  );
};

// Invite Modal Component
interface InviteModalProps {
  board: Board;
  onClose: () => void;
  onInviteSent: () => void;
}

const InviteModal: React.FC<InviteModalProps> = ({ board, onClose, onInviteSent }) => {
  const [username, setUsername] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;

    setIsLoading(true);
    setStatusMessage('');

    try {
      const inviteData: BoardInvite = {
        username: username.trim(),
        message: message.trim() || undefined,
      };
      
      await boardAPI.inviteUser(board.id, inviteData);
      setStatusMessage('Invitation sent successfully!');
      setUsername('');
      setMessage('');
      onInviteSent();
      
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (error: any) {
      if (error.response?.status === 404) {
        setStatusMessage('User not found. Please check the username.');
      } else if (error.response?.status === 400) {
        setStatusMessage(error.response.data.detail || 'Unable to send invitation.');
      } else {
        setStatusMessage('Failed to send invitation. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content invite-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Invite User to "{board.title}"</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          {statusMessage && (
            <div className={`message ${statusMessage.includes('successfully') ? 'success' : 'error'}`}>
              {statusMessage}
            </div>
          )}
          
          <form onSubmit={handleInvite}>
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username to invite"
                required
                autoFocus
              />
            </div>
            
            <div className="form-group">
              <label>Message (optional)</label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Add a personal message to the invitation"
                rows={3}
              />
            </div>
            
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={isLoading}>
                {isLoading ? 'Sending...' : 'Send Invitation'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancel
              </button>
            </div>
          </form>
          
          {/* Current Members */}
          <div className="current-members">
            <h3>Current Members</h3>
            <div className="members-list">
              <div className="member-item owner">
                <div className="member-info">
                  <strong>{board.owner.username}</strong>
                  <span className="member-role">Owner</span>
                </div>
                {board.owner.avatar_url && (
                  <img src={board.owner.avatar_url} alt="Owner" className="member-avatar" />
                )}
              </div>
              
              {board.members.map((member) => (
                <div key={member.id} className="member-item">
                  <div className="member-info">
                    <strong>{member.username}</strong>
                    <span className="member-role">Member</span>
                  </div>
                  {member.avatar_url && (
                    <img src={member.avatar_url} alt={member.username} className="member-avatar" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar; 