import { DragDropContext, DropResult } from '@hello-pangea/dnd';
import { Plus } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { Board as BoardType, Card as CardType } from '../types';
import List from './List';

const Board: React.FC = () => {
  const [board, setBoard] = useState<BoardType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAddingList, setIsAddingList] = useState(false);
  const [newListTitle, setNewListTitle] = useState('');

  useEffect(() => {
    console.log('Board component mounted, loading board...');
    loadBoard();
  }, []);

  const loadBoard = async () => {
    try {
      setLoading(true);
      const boardData = await apiService.getBoard();
      setBoard(boardData);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load board';
      setError(`Failed to load board: ${errorMessage}`);
      console.error('Error loading board:', err);
    } finally {
      setLoading(false);
    }
  };

  const testAPIConnection = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/board');
      const data = await response.json();
      console.log('Direct fetch test:', data);
      alert('API connection test successful! Check console for details.');
    } catch (err) {
      console.error('Direct fetch test failed:', err);
      alert('API connection test failed! Check console for details.');
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
        
        // Remove card from source list
        const [movedCard] = sourceList.cards.splice(source.index, 1);
        
        // Add card to destination list
        destList.cards.splice(newPosition, 0, { ...movedCard, list_id: newListId });
        
        // Update positions
        sourceList.cards.forEach((card, index) => {
          card.position = index;
        });
        destList.cards.forEach((card, index) => {
          card.position = index;
        });
        
        setBoard(newBoard);
      }

      // Make API call
      await apiService.moveCard(cardId, newListId, newPosition);
    } catch (err) {
      console.error('Error moving card:', err);
      // Reload board to get correct state
      await loadBoard();
    }
  };

  const handleCreateList = async () => {
    if (newListTitle.trim()) {
      try {
        const newList = await apiService.createList(newListTitle.trim());
        if (board) {
          const newBoard = {
            ...board,
            lists: [...board.lists, { ...newList, cards: [] }]
          };
          setBoard(newBoard);
        }
        setNewListTitle('');
        setIsAddingList(false);
      } catch (err) {
        console.error('Error creating list:', err);
      }
    }
  };

  const handleCreateCard = async (title: string, description?: string, listId?: number) => {
    try {
      const newCard = await apiService.createCard(title, description, listId);
      if (board) {
        const newBoard = { ...board };
        const listIndex = newBoard.lists.findIndex(list => list.id === listId);
        if (listIndex !== -1) {
          newBoard.lists[listIndex].cards.push(newCard);
          setBoard(newBoard);
        }
      }
    } catch (err) {
      console.error('Error creating card:', err);
    }
  };

  const handleUpdateCard = async (updatedCard: CardType) => {
    // For now, just update the local state
    // In a real app, you'd make an API call to update the card
    if (board) {
      const newBoard = { ...board };
      const listIndex = newBoard.lists.findIndex(list => list.id === updatedCard.list_id);
      if (listIndex !== -1) {
        const cardIndex = newBoard.lists[listIndex].cards.findIndex(card => card.id === updatedCard.id);
        if (cardIndex !== -1) {
          newBoard.lists[listIndex].cards[cardIndex] = updatedCard;
          setBoard(newBoard);
        }
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

  if (loading) {
    return (
      <div className="loading">
        <p>Loading board...</p>
        <button onClick={testAPIConnection} style={{ marginTop: '1rem', padding: '0.5rem 1rem', backgroundColor: '#0079bf', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Test API Connection
        </button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error">
        <p>{error}</p>
        <button onClick={loadBoard} style={{ marginTop: '1rem', padding: '0.5rem 1rem', backgroundColor: '#0079bf', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Retry
        </button>
        <button onClick={testAPIConnection} style={{ marginTop: '1rem', marginLeft: '1rem', padding: '0.5rem 1rem', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Test API Connection
        </button>
      </div>
    );
  }

  if (!board) {
    return <div className="error">Board not found</div>;
  }

  return (
    <div className="board">
      <header className="board-header">
        <h1 className="board-title">{board.title}</h1>
      </header>
      
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

export default Board; 