export interface Card {
  id: number;
  title: string;
  description?: string;
  list_id: number;
  position: number;
  checklist: string[];
  created_at: string;
  updated_at: string;
}

export interface TaskList {
  id: number;
  title: string;
  position: number;
  cards: Card[];
  created_at: string;
}

export interface Board {
  id: number;
  title: string;
  description?: string;
  lists: TaskList[];
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
}

export interface LoginData {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface BoardCreate {
  title: string;
  description?: string;
}

export interface ListCreate {
  title: string;
  board_id: number;
}

export interface CardCreate {
  title: string;
  description?: string;
  list_id: number;
}

export interface DragResult {
  draggableId: string;
  type: string;
  source: {
    droppableId: string;
    index: number;
  };
  destination?: {
    droppableId: string;
    index: number;
  };
}
