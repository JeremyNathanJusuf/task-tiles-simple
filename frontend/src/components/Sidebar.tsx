import { Plus, Trash2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { Board } from '../types';

interface SidebarProps {
  selectedBoardId: number | null;
  onSelectBoard: (boardId: number | null) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ selectedBoardId, onSelectBoard }) => {
  const [boards, setBoards] = useState<Board[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newBoardTitle, setNewBoardTitle] = useState('');

  useEffect(() => {
    loadBoards();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadBoards = async () => {
    try {
      setLoading(true);
      const boardsData = await apiService.getBoards();
      setBoards(boardsData);
      setError(null);
      
      // Auto-select first board if none selected
      if (!selectedBoardId && boardsData.length > 0) {
        onSelectBoard(boardsData[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load boards');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBoard = async () => {
    if (!newBoardTitle.trim()) return;

    try {
      const newBoard = await apiService.createBoard({
        title: newBoardTitle.trim(),
      });
      setBoards([...boards, newBoard]);
      setNewBoardTitle('');
      setIsCreating(false);
      onSelectBoard(newBoard.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create board');
    }
  };

  const handleDeleteBoard = async (boardId: number) => {
    if (!window.confirm('Are you sure you want to delete this board?')) return;

    try {
      await apiService.deleteBoard(boardId);
      const updatedBoards = boards.filter(board => board.id !== boardId);
      setBoards(updatedBoards);
      
      // If deleted board was selected, select another one
      if (selectedBoardId === boardId) {
        const nextBoard = updatedBoards[0];
        onSelectBoard(nextBoard ? nextBoard.id : null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete board');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleCreateBoard();
    }
    if (e.key === 'Escape') {
      setIsCreating(false);
      setNewBoardTitle('');
    }
  };

  if (loading) {
    return (
      <div className="sidebar">
        <div className="sidebar-header">
          <h3>Boards</h3>
        </div>
        <div className="sidebar-loading">Loading boards...</div>
      </div>
    );
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h3>Your Boards</h3>
        <button 
          onClick={() => setIsCreating(true)}
          className="add-board-btn"
          title="Create new board"
        >
          <Plus size={16} />
        </button>
      </div>

      {error && <div className="sidebar-error">{error}</div>}

      <div className="boards-list">
        {boards.map((board) => (
          <div
            key={board.id}
            className={`board-item ${selectedBoardId === board.id ? 'selected' : ''}`}
            onClick={() => onSelectBoard(board.id)}
          >
            <div className="board-info">
              <h4>{board.title}</h4>
              <span className="board-stats">
                {board.lists.length} lists • {board.lists.reduce((acc, list) => acc + list.cards.length, 0)} cards
              </span>
            </div>
            <div className="board-actions">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteBoard(board.id);
                }}
                className="delete-board-btn"
                title="Delete board"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}

        {isCreating && (
          <div className="create-board-form">
            <input
              type="text"
              value={newBoardTitle}
              onChange={(e) => setNewBoardTitle(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter board title..."
              className="board-title-input"
              autoFocus
            />
            <div className="create-board-actions">
              <button onClick={handleCreateBoard} className="save-btn">
                Create
              </button>
              <button 
                onClick={() => {
                  setIsCreating(false);
                  setNewBoardTitle('');
                }}
                className="cancel-btn"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {boards.length === 0 && !isCreating && (
          <div className="empty-state">
            <p>No boards yet</p>
            <button onClick={() => setIsCreating(true)} className="create-first-board">
              Create your first board
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar; 