import { Droppable } from '@hello-pangea/dnd';
import { Plus, X } from 'lucide-react';
import React, { useState } from 'react';
import { Card as CardType, TaskList } from '../types';
import Card from './Card';

interface ListProps {
  list: TaskList;
  onCreateCard: (title: string, description?: string, listId?: number) => void;
  onUpdateCard?: (card: CardType) => void;
}

const List: React.FC<ListProps> = ({ list, onCreateCard, onUpdateCard }) => {
  const [isAddingCard, setIsAddingCard] = useState(false);
  const [newCardTitle, setNewCardTitle] = useState('');
  const [newCardDescription, setNewCardDescription] = useState('');

  const handleAddCard = () => {
    if (newCardTitle.trim()) {
      onCreateCard(newCardTitle.trim(), newCardDescription.trim() || undefined, list.id);
      setNewCardTitle('');
      setNewCardDescription('');
      setIsAddingCard(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAddCard();
    }
    if (e.key === 'Escape') {
      setIsAddingCard(false);
      setNewCardTitle('');
      setNewCardDescription('');
    }
  };

  return (
    <div className="list">
      <div className="list-header">
        <h2 className="list-title">{list.title}</h2>
        <span className="card-count">{list.cards.length}</span>
      </div>
      
      <Droppable droppableId={list.id.toString()}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={`cards-container ${snapshot.isDraggingOver ? 'dragging-over' : ''}`}
          >
            {list.cards.map((card, index) => (
              <Card
                key={card.id}
                card={card}
                index={index}
                onUpdateCard={onUpdateCard}
              />
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
      
      {isAddingCard ? (
        <div className="add-card-form">
          <textarea
            value={newCardTitle}
            onChange={(e) => setNewCardTitle(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter a title for this card..."
            className="card-title-input"
            autoFocus
          />
          <textarea
            value={newCardDescription}
            onChange={(e) => setNewCardDescription(e.target.value)}
            placeholder="Enter a description (optional)..."
            className="card-description-input"
          />
          <div className="add-card-actions">
            <button
              onClick={handleAddCard}
              className="add-card-btn"
              disabled={!newCardTitle.trim()}
            >
              Add Card
            </button>
            <button
              onClick={() => {
                setIsAddingCard(false);
                setNewCardTitle('');
                setNewCardDescription('');
              }}
              className="cancel-btn"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setIsAddingCard(true)}
          className="add-card-trigger"
        >
          <Plus size={16} />
          Add a card
        </button>
      )}
    </div>
  );
};

export default List; 