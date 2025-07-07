export interface Card {
  id: number;
  title: string;
  description?: string;
  list_id: number;
  position: number;
  checklist: string[];
  created_at: string;
  updated_at: string;
  creator: User;
  contributors: Contributor[];
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
  owner: User;
  members: User[];
  is_shared: boolean;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
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

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  is_active: boolean;
}

export interface UserUpdate {
  full_name?: string;
  email?: string;
  avatar_url?: string;
}

export interface PasswordUpdate {
  current_password: string;
  new_password: string;
}

export interface BoardInvite {
  username: string;
  message?: string;
}

export interface Invitation {
  id: number;
  board_id: number;
  board_title: string;
  inviter: User;
  message?: string;
  status: string;
  created_at: string;
}

export interface InvitationResponse {
  accept: boolean;
}

export interface Contributor {
  id: number;
  username: string;
  full_name?: string;
  avatar_url?: string;
  contributed_at: string;
}

export interface CardUpdate {
  title?: string;
  description?: string;
  checklist?: string[];
}

export interface MoveCard {
  new_list_id: number;
  new_position: number;
}

export interface DragItem {
  id: number;
  type: "card";
  originalListId: number;
  originalPosition: number;
}
