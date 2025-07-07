import React, { useState } from 'react';
import { cardAPI, listAPI } from '../services/api';
import { Board, Card, CardCreate, CardUpdate, ListCreate, TaskList, UserProfile } from '../types';

interface BoardViewProps {
  board: Board;
  onBoardUpdate: () => void;
  user: UserProfile | null;
}

const BoardView: React.FC<BoardViewProps> = ({ board, onBoardUpdate, user }) => {
  const [selectedCard, setSelectedCard] = useState<Card | null>(null);
  const [showCardModal, setShowCardModal] = useState(false);

  const handleCreateList = async (title: string) => {
    try {
      const listData: ListCreate = {
        title,
        board_id: board.id,
      };
      await listAPI.createList(listData);
      onBoardUpdate();
    } catch (error) {
      console.error('Failed to create list:', error);
    }
  };

  const handleCreateCard = async (listId: number, title: string) => {
    try {
      const cardData: CardCreate = {
        title,
        list_id: listId,
      };
      await cardAPI.createCard(cardData);
      onBoardUpdate();
    } catch (error) {
      console.error('Failed to create card:', error);
    }
  };

  const handleUpdateCard = async (cardId: number, updates: CardUpdate) => {
    try {
      await cardAPI.updateCard(cardId, updates);
      onBoardUpdate();
      setShowCardModal(false);
    } catch (error) {
      console.error('Failed to update card:', error);
    }
  };

  const handleMoveCard = async (cardId: number, newListId: number, newPosition: number) => {
    try {
      await cardAPI.moveCard(cardId, {
        new_list_id: newListId,
        new_position: newPosition,
      });
      onBoardUpdate();
    } catch (error) {
      console.error('Failed to move card:', error);
    }
  };

  const handleDeleteCard = async (cardId: number) => {
    try {
      await cardAPI.deleteCard(cardId);
      onBoardUpdate();
      setShowCardModal(false);
    } catch (error) {
      console.error('Failed to delete card:', error);
    }
  };

  const handleDeleteList = async (listId: number) => {
    try {
      await listAPI.deleteList(listId);
      onBoardUpdate();
    } catch (error) {
      console.error('Failed to delete list:', error);
    }
  };

  const openCardModal = (card: Card) => {
    setSelectedCard(card);
    setShowCardModal(true);
  };

  const closeCardModal = () => {
    setSelectedCard(null);
    setShowCardModal(false);
  };

  return (
    <div className="board-view">
      <div className="board-header">
        <h1>{board.title}</h1>
        {board.description && <p className="board-description">{board.description}</p>}
        <div className="board-info">
          <span className="board-owner">Owner: {board.owner.username}</span>
          {board.is_shared && (
            <span className="board-members">
              {board.members.length + 1} member{board.members.length === 0 ? '' : 's'}
            </span>
          )}
        </div>
      </div>

      <div className="board-content">
        <div className="lists-container">
          {board.lists.map((list) => (
            <ListComponent
              key={list.id}
              list={list}
              onCreateCard={handleCreateCard}
              onUpdateCard={handleUpdateCard}
              onMoveCard={handleMoveCard}
              onDeleteCard={handleDeleteCard}
              onDeleteList={handleDeleteList}
              onCardClick={openCardModal}
              user={user}
            />
          ))}
          <AddListComponent onCreateList={handleCreateList} />
        </div>
      </div>

      {/* Card Detail Modal */}
      {showCardModal && selectedCard && (
        <CardDetailModal
          card={selectedCard}
          onClose={closeCardModal}
          onUpdate={handleUpdateCard}
          onDelete={handleDeleteCard}
          user={user}
        />
      )}
    </div>
  );
};

// List Component
interface ListComponentProps {
  list: TaskList;
  onCreateCard: (listId: number, title: string) => void;
  onUpdateCard: (cardId: number, updates: CardUpdate) => void;
  onMoveCard: (cardId: number, newListId: number, newPosition: number) => void;
  onDeleteCard: (cardId: number) => void;
  onDeleteList: (listId: number) => void;
  onCardClick: (card: Card) => void;
  user: UserProfile | null;
}

const ListComponent: React.FC<ListComponentProps> = ({
  list,
  onCreateCard,
  onDeleteCard,
  onDeleteList,
  onCardClick,
}) => {
  const [showAddCard, setShowAddCard] = useState(false);
  const [newCardTitle, setNewCardTitle] = useState('');

  const handleAddCard = () => {
    if (newCardTitle.trim()) {
      onCreateCard(list.id, newCardTitle.trim());
      setNewCardTitle('');
      setShowAddCard(false);
    }
  };

  const handleDeleteList = () => {
    if (window.confirm(`Delete list "${list.title}"? This will also delete all cards in the list.`)) {
      onDeleteList(list.id);
    }
  };

  const getUserInitials = (username: string, fullName?: string): string => {
    if (fullName) {
      return fullName.split(' ').map(n => n[0]).join('').toUpperCase();
    }
    return username.substring(0, 2).toUpperCase();
  };

  const getUniqueContributors = (card: Card) => {
    const contributorMap = new Map();
    
    // Add creator
    contributorMap.set(card.creator.id, card.creator);
    
    // Add contributors (this will override creator if they're also a contributor)
    card.contributors.forEach(contributor => {
      contributorMap.set(contributor.id, {
        id: contributor.id,
        username: contributor.username,
        full_name: contributor.full_name,
        avatar_url: contributor.avatar_url,
      });
    });
    
    return Array.from(contributorMap.values());
  };

  return (
    <div className="list">
      <div className="list-header">
        <h3>{list.title}</h3>
        <button 
          className="btn btn-sm btn-danger"
          onClick={handleDeleteList}
          title="Delete list"
        >
          🗑️
        </button>
      </div>

      <div className="cards-container">
        {list.cards.map((card) => {
          const uniqueContributors = getUniqueContributors(card);
          
          return (
            <div
              key={card.id}
              className="card"
              onClick={() => onCardClick(card)}
            >
              <div className="card-content">
                <h4 className="card-title">{card.title}</h4>
                {card.description && (
                  <p className="card-description">{card.description}</p>
                )}
                
                {card.checklist && card.checklist.length > 0 && (
                  <div className="card-checklist">
                    <span className="checklist-indicator">
                      ✓ {card.checklist.length} item{card.checklist.length === 1 ? '' : 's'}
                    </span>
                  </div>
                )}
              </div>

              <div className="card-footer">
                <div className="card-contributors">
                  {uniqueContributors.slice(0, 3).map((contributor) => (
                    <div
                      key={contributor.id}
                      className="contributor-avatar"
                      title={`${contributor.username}${contributor.full_name ? ` (${contributor.full_name})` : ''}`}
                    >
                      {contributor.avatar_url ? (
                        <img src={contributor.avatar_url} alt={contributor.username} />
                      ) : (
                        <span className="contributor-initials">
                          {getUserInitials(contributor.username, contributor.full_name)}
                        </span>
                      )}
                    </div>
                  ))}
                  {uniqueContributors.length > 3 && (
                    <div className="contributor-more">+{uniqueContributors.length - 3}</div>
                  )}
                </div>

                <div className="card-actions">
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm('Delete this card?')) {
                        onDeleteCard(card.id);
                      }
                    }}
                    title="Delete card"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="add-card-section">
        {showAddCard ? (
          <div className="add-card-form">
            <input
              type="text"
              value={newCardTitle}
              onChange={(e) => setNewCardTitle(e.target.value)}
              placeholder="Enter card title..."
              autoFocus
              onKeyPress={(e) => e.key === 'Enter' && handleAddCard()}
            />
            <div className="form-actions">
              <button className="btn btn-primary btn-sm" onClick={handleAddCard}>
                Add Card
              </button>
              <button 
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setShowAddCard(false);
                  setNewCardTitle('');
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button 
            className="btn btn-light add-card-btn"
            onClick={() => setShowAddCard(true)}
          >
            + Add a card
          </button>
        )}
      </div>
    </div>
  );
};

// Add List Component
interface AddListComponentProps {
  onCreateList: (title: string) => void;
}

const AddListComponent: React.FC<AddListComponentProps> = ({ onCreateList }) => {
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');

  const handleSubmit = () => {
    if (title.trim()) {
      onCreateList(title.trim());
      setTitle('');
      setShowForm(false);
    }
  };

  return (
    <div className="add-list">
      {showForm ? (
        <div className="add-list-form">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter list title..."
            autoFocus
            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
          />
          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleSubmit}>
              Add List
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => {
                setShowForm(false);
                setTitle('');
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button 
          className="btn btn-light add-list-btn"
          onClick={() => setShowForm(true)}
        >
          + Add another list
        </button>
      )}
    </div>
  );
};

// Card Detail Modal
interface CardDetailModalProps {
  card: Card;
  onClose: () => void;
  onUpdate: (cardId: number, updates: CardUpdate) => void;
  onDelete: (cardId: number) => void;
  user: UserProfile | null;
}

const CardDetailModal: React.FC<CardDetailModalProps> = ({
  card,
  onClose,
  onUpdate,
  onDelete,
}) => {
  const [title, setTitle] = useState(card.title);
  const [description, setDescription] = useState(card.description || '');
  const [checklist, setChecklist] = useState<string[]>(card.checklist || []);
  const [newChecklistItem, setNewChecklistItem] = useState('');

  const handleSave = () => {
    const updates: CardUpdate = {
      title: title.trim(),
      description: description.trim() || undefined,
      checklist,
    };
    onUpdate(card.id, updates);
  };

  const handleAddChecklistItem = () => {
    if (newChecklistItem.trim()) {
      setChecklist([...checklist, newChecklistItem.trim()]);
      setNewChecklistItem('');
    }
  };

  const handleRemoveChecklistItem = (index: number) => {
    setChecklist(checklist.filter((_, i) => i !== index));
  };

  const getUserInitials = (username: string, fullName?: string): string => {
    if (fullName) {
      return fullName.split(' ').map(n => n[0]).join('').toUpperCase();
    }
    return username.substring(0, 2).toUpperCase();
  };

  const getUniqueContributors = (card: Card) => {
    const contributorMap = new Map();
    
    // Add creator
    contributorMap.set(card.creator.id, {
      ...card.creator,
      role: 'Creator',
    });
    
    // Add contributors
    card.contributors.forEach(contributor => {
      if (contributor.id !== card.creator.id) {
        contributorMap.set(contributor.id, {
          ...contributor,
          role: 'Contributor',
        });
      }
    });
    
    return Array.from(contributorMap.values());
  };

  const uniqueContributors = getUniqueContributors(card);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content card-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Card Details</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div className="card-detail-content">
            <div className="card-detail-main">
              <div className="form-group">
                <label>Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Card title"
                />
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Add a description..."
                  rows={4}
                />
              </div>

              <div className="form-group">
                <label>Checklist</label>
                <div className="checklist-container">
                  {checklist.map((item, index) => (
                    <div key={index} className="checklist-item">
                      <span>{item}</span>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => handleRemoveChecklistItem(index)}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <div className="add-checklist-item">
                    <input
                      type="text"
                      value={newChecklistItem}
                      onChange={(e) => setNewChecklistItem(e.target.value)}
                      placeholder="Add checklist item..."
                      onKeyPress={(e) => e.key === 'Enter' && handleAddChecklistItem()}
                    />
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={handleAddChecklistItem}
                    >
                      Add
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="card-detail-sidebar">
              <div className="contributors-section">
                <h3>Contributors</h3>
                <div className="contributors-list">
                  {uniqueContributors.map((contributor) => (
                    <div key={contributor.id} className="contributor-item">
                      <div className="contributor-avatar">
                        {contributor.avatar_url ? (
                          <img src={contributor.avatar_url} alt={contributor.username} />
                        ) : (
                          <span className="contributor-initials">
                            {getUserInitials(contributor.username, contributor.full_name)}
                          </span>
                        )}
                      </div>
                      <div className="contributor-info">
                        <strong>{contributor.username}</strong>
                        {contributor.full_name && <span>{contributor.full_name}</span>}
                        <span className="contributor-role">{contributor.role}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card-info">
                <h3>Card Info</h3>
                <div className="info-item">
                  <strong>Created:</strong> {new Date(card.created_at).toLocaleDateString()}
                </div>
                <div className="info-item">
                  <strong>Updated:</strong> {new Date(card.updated_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-primary" onClick={handleSave}>
            Save Changes
          </button>
          <button
            className="btn btn-danger"
            onClick={() => {
              if (window.confirm('Delete this card?')) {
                onDelete(card.id);
              }
            }}
          >
            Delete Card
          </button>
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default BoardView; 