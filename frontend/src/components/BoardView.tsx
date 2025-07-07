import { DragDropContext, DropResult } from '@hello-pangea/dnd';
import { Plus } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { Board, Card as CardType } from '../types';
import List from './List';

interface BoardViewProps {
  boardId: number | null;
}

const BoardView: React.FC<BoardViewProps> = ({ boardId }) => {
  const [board, setBoard] = useState<Board | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAddingList, setIsAddingList] = useState(false);
  const [newListTitle, setNewListTitle] = useState('');

  useEffect(() => {
    if (boardId) {
      loadBoard();
    } else {
      setBoard(null);
    }
  }, [boardId]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadBoard = async () => {
    if (!boardId) return;

    try {
      setLoading(true);
      const boardData = await apiService.getBoard(boardId);
      setBoard(boardData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load board');
    } finally {
      setLoading(false);
    }
  };

  const handleDragEnd = async (result: DropResult) => {
    if (!result.destination || !board) return;

    const { source, destination, draggableId } = result;
    
    if (source.droppableId === destination.droppableId && source.index === destination.index) {
      return;
    }

    try {
      const cardId = parseInt(draggableId);
      const newListId = parseInt(destination.droppableId);
      const newPosition = destination.index;

      // Optimistically update the UI
      const newBoard = { ...board };
      const sourceListIndex = newBoard.lists.findIndex(list => list.id === parseInt(source.droppableId));
      const destListIndex = newBoard.lists.findIndex(list => list.id === newListId);
      
      if (sourceListIndex !== -1 && destListIndex !== -1) {
        const sourceList = newBoard.lists[sourceListIndex];
        const destList = newBoard.lists[destListIndex];
        
        const [movedCard] = sourceList.cards.splice(source.index, 1);
        destList.cards.splice(newPosition, 0, { ...movedCard, list_id: newListId });
        
        sourceList.cards.forEach((card, index) => {
          card.position = index;
        });
        destList.cards.forEach((card, index) => {
          card.position = index;
        });
        
        setBoard(newBoard);
      }

      await apiService.moveCard(cardId, newListId, newPosition);
    } catch (err) {
      console.error('Error moving card:', err);
      await loadBoard();
    }
  };

  const handleCreateList = async () => {
    if (!newListTitle.trim() || !board) return;

    try {
      const newList = await apiService.createList({
        title: newListTitle.trim(),
        board_id: board.id
      });
      
      const updatedBoard = {
        ...board,
        lists: [...board.lists, { ...newList, cards: [] }]
      };
      setBoard(updatedBoard);
      setNewListTitle('');
      setIsAddingList(false);
    } catch (err) {
      console.error('Error creating list:', err);
    }
  };

  const handleCreateCard = async (title: string, description?: string, listId?: number) => {
    if (!listId || !board) return;
    
    try {
      const newCard = await apiService.createCard({
        title,
        description,
        list_id: listId
      });
      
      const newBoard = { ...board };
      const listIndex = newBoard.lists.findIndex(list => list.id === listId);
      if (listIndex !== -1) {
        newBoard.lists[listIndex].cards.push(newCard);
        setBoard(newBoard);
      }
    } catch (err) {
      console.error('Error creating card:', err);
    }
  };

  const handleUpdateCard = async (updatedCard: CardType) => {
    if (!board) return;
    
    const newBoard = { ...board };
    const listIndex = newBoard.lists.findIndex(list => list.id === updatedCard.list_id);
    if (listIndex !== -1) {
      const cardIndex = newBoard.lists[listIndex].cards.findIndex(card => card.id === updatedCard.id);
      if (cardIndex !== -1) {
        newBoard.lists[listIndex].cards[cardIndex] = updatedCard;
        setBoard(newBoard);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleCreateList();
    }
    if (e.key === 'Escape') {
      setIsAddingList(false);
      setNewListTitle('');
    }
  };

  if (!boardId) {
    return (
      <div className="board-view">
        <div className="empty-board">
          <h2>Select a board to get started</h2>
          <p>Choose a board from the sidebar to view and manage your tasks</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="board-view">
        <div className="board-loading">Loading board...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="board-view">
        <div className="board-error">
          <h3>Error loading board</h3>
          <p>{error}</p>
          <button onClick={loadBoard} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!board) {
    return (
      <div className="board-view">
        <div className="board-error">
          <h3>Board not found</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="board-view">
      <div className="board-header">
        <h1>{board.title}</h1>
        {board.description && <p className="board-description">{board.description}</p>}
      </div>

      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="board-content">
          <div className="lists-container">
            {board.lists.map((list) => (
              <List
                key={list.id}
                list={list}
                onCreateCard={handleCreateCard}
                onUpdateCard={handleUpdateCard}
              />
            ))}
            
            {isAddingList ? (
              <div className="add-list-form">
                <input
                  type="text"
                  value={newListTitle}
                  onChange={(e) => setNewListTitle(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter list title..."
                  className="list-title-input"
                  autoFocus
                />
                <div className="add-list-actions">
                  <button
                    onClick={handleCreateList}
                    className="add-list-btn"
                    disabled={!newListTitle.trim()}
                  >
                    Add List
                  </button>
                  <button
                    onClick={() => {
                      setIsAddingList(false);
                      setNewListTitle('');
                    }}
                    className="cancel-btn"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setIsAddingList(true)}
                className="add-list-trigger"
              >
                <Plus size={16} />
                Add another list
              </button>
            )}
          </div>
        </div>
      </DragDropContext>
    </div>
  );
};

export default BoardView; 