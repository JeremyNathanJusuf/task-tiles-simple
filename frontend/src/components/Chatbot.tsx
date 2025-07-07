import React, { useEffect, useRef, useState } from 'react';
import { chatbotAPI } from '../services/api';
import { Board, UserProfile } from '../types';

interface ChatbotProps {
  user: UserProfile | null;
  currentBoard?: Board | null;
  onBoardsUpdate?: () => void;
  onBoardChange?: (boardId: number) => void;
}

interface ChatbotAction {
  action?: string;
  data?: any;
}

interface ChatMessage {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  role: 'user' | 'assistant';
}

interface ChatbotAction {
  action?: string;
  data?: any;
}

const Chatbot: React.FC<ChatbotProps> = ({ user, currentBoard, onBoardsUpdate, onBoardChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      text: currentBoard 
        ? `Hi! I'm your AI task management assistant powered by OpenAI. I can see you're working on the "${currentBoard.title}" board. I can help you with your boards, lists, and cards using natural language. I remember our conversation and understand your current board context!`
        : "Hi! I'm your AI task management assistant powered by OpenAI. I can help you with your boards, lists, and cards using natural language. I remember our conversation, so feel free to reference previous topics! Try asking me to create something or check your tasks!",
      isUser: false,
      timestamp: new Date(),
      role: 'assistant'
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // Update welcome message when board changes
  useEffect(() => {
    if (messages.length === 1) { // Only update if it's just the welcome message
      const newWelcomeMessage = {
        id: '1',
        text: currentBoard 
          ? `Hi! I'm your AI task management assistant powered by OpenAI. I can see you're working on the "${currentBoard.title}" board. I can help you with your boards, lists, and cards using natural language. I remember our conversation and understand your current board context!`
          : "Hi! I'm your AI task management assistant powered by OpenAI. I can help you with your boards, lists, and cards using natural language. I remember our conversation, so feel free to reference previous topics! Try asking me to create something or check your tasks!",
        isUser: false,
        timestamp: new Date(),
        role: 'assistant' as const
      };
      setMessages([newWelcomeMessage]);
    }
  }, [currentBoard?.id, currentBoard?.title]);

  // Auto-resize textarea based on content
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const lineHeight = 20; // Approximate line height
      const maxLines = 5;
      const maxHeight = lineHeight * maxLines;
      
      const newHeight = Math.min(textarea.scrollHeight, maxHeight);
      textarea.style.height = `${newHeight}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputText]);

  const toggleChatbot = () => {
    setIsOpen(!isOpen);
  };

  // Convert messages to conversation history format for API
  const getConversationHistory = () => {
    return messages.slice(1).map(msg => ({
      role: msg.role,
      content: msg.text,
      timestamp: msg.timestamp.toISOString()
    }));
  };

  // Build current board context for API
  const getCurrentBoardContext = () => {
    if (!currentBoard) return undefined;

    return {
      board_id: currentBoard.id,
      board_title: currentBoard.title,
      board_description: currentBoard.description,
      lists: currentBoard.lists.map(list => ({
        id: list.id,
        title: list.title,
        cards_count: list.cards.length
      })),
      recent_cards: currentBoard.lists
        .flatMap(list => 
          list.cards.map(card => ({
            id: card.id,
            title: card.title,
            list_name: list.title
          }))
        )
        .slice(-10) // Last 10 cards for context
    };
  };

  // Handle actions returned from chatbot API
  const handleChatbotAction = (action?: ChatbotAction) => {
    if (!action?.action) return;

    // Trigger immediate UI updates based on the action
    switch (action.action) {
      case 'board_created':
      case 'list_created':
      case 'card_created':
      case 'card_moved':
      case 'card_deleted':
      case 'list_deleted':
        // For create/modify actions, ensure a more robust refresh
        if (onBoardsUpdate) {
          // Use setTimeout to ensure backend consistency
          setTimeout(() => {
            onBoardsUpdate();
          }, 100); // Small delay to ensure backend state is consistent
        }
        
        // If a specific board was affected and it's different from current board
        if (action.data?.board_id && onBoardChange && currentBoard?.id !== action.data.board_id) {
          setTimeout(() => {
            onBoardChange(action.data!.board_id);
          }, 300); // Slightly longer delay for board switching
        }
        break;
        
      case 'show_boards':
      case 'show_tasks':
      case 'board_info':
        // For info requests, just refresh current view
        if (onBoardsUpdate) {
          onBoardsUpdate();
        }
        break;
        
      default:
        // For other actions, just refresh boards to be safe
        if (onBoardsUpdate) {
          setTimeout(() => {
            onBoardsUpdate();
          }, 100);
        }
        break;
    }
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      text: inputText,
      isUser: true,
      timestamp: new Date(),
      role: 'user'
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const conversationHistory = getConversationHistory();
      const currentBoardContext = getCurrentBoardContext();
      const response = await chatbotAPI.sendMessage(inputText, conversationHistory, currentBoardContext);
      
      const botMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: response.data.message,
        isUser: false,
        timestamp: new Date(),
        role: 'assistant'
      };

      setMessages(prev => [...prev, botMessage]);

      // Handle any actions that require UI updates
      handleChatbotAction(response.data);

    } catch (error) {
      console.error('Chatbot API error:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: "Sorry, I encountered an error. Please make sure the OpenAI API key is configured properly.",
        isUser: false,
        timestamp: new Date(),
        role: 'assistant'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await transcribeAudio(audioBlob);
        
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAudio = async (audioBlob: Blob) => {
    setIsTranscribing(true);
    try {
      const response = await chatbotAPI.voiceToText(audioBlob);
      setInputText(response.data.text);
    } catch (error) {
      console.error('Transcription error:', error);
      alert('Failed to transcribe audio. Please try again or check if OpenAI API key is configured.');
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleVoiceInput = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
  };

  const clearConversation = () => {
    const newWelcomeMessage = {
      id: '1',
      text: currentBoard 
        ? `Hi! I'm your AI task management assistant powered by OpenAI. I can see you're working on the "${currentBoard.title}" board. I can help you with your boards, lists, and cards using natural language. I remember our conversation and understand your current board context!`
        : "Hi! I'm your AI task management assistant powered by OpenAI. I can help you with your boards, lists, and cards using natural language. I remember our conversation, so feel free to reference previous topics! Try asking me to create something or check your tasks!",
      isUser: false,
      timestamp: new Date(),
      role: 'assistant' as const
    };
    setMessages([newWelcomeMessage]);
  };

  return (
    <>
      {/* Floating Chatbot Icon */}
      <div className="chatbot-fab" onClick={toggleChatbot}>
        <div className="chatbot-icon">
          {isOpen ? '×' : '🤖'}
        </div>
        {!isOpen && (
          <div className="chatbot-tooltip">
            {currentBoard 
              ? `Ask me about your "${currentBoard.title}" board!`
              : "Ask me anything about your tasks!"
            }
          </div>
        )}
      </div>

      {/* Chatbot Modal */}
      {isOpen && (
        <div className="chatbot-modal">
          <div className="chatbot-header">
            <div className="chatbot-title">
              <span className="chatbot-avatar">🤖</span>
              <div>
                <h3>AI Task Assistant</h3>
                <span className="chatbot-status">
                  Powered by OpenAI • Memory Enabled
                  {currentBoard && ` • Working on "${currentBoard.title}"`}
                </span>
              </div>
            </div>
            <div className="chatbot-controls">
              <button 
                className="chatbot-clear" 
                onClick={clearConversation}
                title="Clear conversation history"
              >
                🗑️
              </button>
              <button className="chatbot-close" onClick={toggleChatbot}>×</button>
            </div>
          </div>

          <div className="chatbot-messages">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`chatbot-message ${message.isUser ? 'user' : 'bot'}`}
              >
                <div className="message-content">
                  <p>{message.text}</p>
                  <span className="message-time">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="chatbot-message bot">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chatbot-input">
            <div className="input-container">
              <textarea
                ref={textareaRef}
                value={inputText}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder={
                  isTranscribing 
                    ? "Transcribing..." 
                    : currentBoard
                    ? `Ask about "${currentBoard.title}" board or tell me to create something...`
                    : "Ask about your tasks or tell me to create something..."
                }
                disabled={isLoading || isTranscribing}
                className="expandable-textarea"
              />
              <div className="input-actions">
                <button
                  className={`voice-btn ${isRecording ? 'recording' : ''} ${isTranscribing ? 'transcribing' : ''}`}
                  onClick={handleVoiceInput}
                  disabled={isLoading || isTranscribing}
                  title={isRecording ? "Stop recording" : "Voice input with Whisper"}
                >
                  {isTranscribing ? '⏳' : isRecording ? '⏹️' : '🎤'}
                </button>
                <button
                  className="send-btn"
                  onClick={handleSendMessage}
                  disabled={!inputText.trim() || isLoading || isTranscribing}
                  title="Send message"
                >
                  ➤
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Chatbot; 