import { Draggable } from '@hello-pangea/dnd';
import { CheckSquare, Plus, Square, X } from 'lucide-react';
import React, { useState } from 'react';
import { Card as CardType } from '../types';

interface CardProps {
  card: CardType;
  index: number;
  onUpdateCard?: (card: CardType) => void;
}

const Card: React.FC<CardProps> = ({ card, index, onUpdateCard }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [showChecklist, setShowChecklist] = useState(false);
  const [newChecklistItem, setNewChecklistItem] = useState('');

  const handleAddChecklistItem = () => {
    if (newChecklistItem.trim()) {
      const updatedCard = {
        ...card,
        checklist: [...card.checklist, newChecklistItem.trim()]
      };
      onUpdateCard?.(updatedCard);
      setNewChecklistItem('');
    }
  };

  const handleRemoveChecklistItem = (itemIndex: number) => {
    const updatedCard = {
      ...card,
      checklist: card.checklist.filter((_, index) => index !== itemIndex)
    };
    onUpdateCard?.(updatedCard);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAddChecklistItem();
    }
  };

  return (
    <Draggable draggableId={card.id.toString()} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          className={`card ${snapshot.isDragging ? 'dragging' : ''}`}
        >
          <div className="card-header">
            <h3 className="card-title">{card.title}</h3>
            <button
              className="checklist-toggle"
              onClick={() => setShowChecklist(!showChecklist)}
              title="Toggle checklist"
            >
              <CheckSquare size={16} />
            </button>
          </div>
          
          {card.description && (
            <p className="card-description">{card.description}</p>
          )}
          
          {card.checklist.length > 0 && (
            <div className="checklist-summary">
              <CheckSquare size={14} />
              <span>{card.checklist.length} items</span>
            </div>
          )}
          
          {showChecklist && (
            <div className="checklist">
              <div className="checklist-header">
                <CheckSquare size={16} />
                <span>Checklist</span>
              </div>
              
              <div className="checklist-items">
                {card.checklist.map((item, index) => (
                  <div key={index} className="checklist-item">
                    <Square size={14} />
                    <span>{item}</span>
                    <button
                      className="remove-item"
                      onClick={() => handleRemoveChecklistItem(index)}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
              
              <div className="add-checklist-item">
                <input
                  type="text"
                  value={newChecklistItem}
                  onChange={(e) => setNewChecklistItem(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Add an item..."
                  className="checklist-input"
                />
                <button
                  onClick={handleAddChecklistItem}
                  className="add-item-btn"
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </Draggable>
  );
};

export default Card; 