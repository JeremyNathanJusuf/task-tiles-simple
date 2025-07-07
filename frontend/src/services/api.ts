import axios from "axios";
import {
  AuthResponse,
  Board,
  BoardCreate,
  Card,
  CardCreate,
  ListCreate,
  LoginData,
  RegisterData,
  TaskList,
  User,
} from "../types";

// Use environment variable or fallback to current host with different port
const API_BASE_URL = process.env.REACT_APP_API_URL
  ? `${process.env.REACT_APP_API_URL}/api`
  : `${window.location.protocol}//${window.location.hostname}:8000/api`;
console.log("API_BASE_URL:", API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/";
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  // Authentication
  register: async (data: RegisterData): Promise<User> => {
    const response = await api.post("/register", data);
    return response.data;
  },

  login: async (data: LoginData): Promise<AuthResponse> => {
    const response = await api.post("/login", data);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get("/me");
    return response.data;
  },

  // Boards
  getBoards: async (): Promise<Board[]> => {
    try {
      console.log("Making API request to:", `${API_BASE_URL}/boards`);
      const response = await api.get("/boards");
      console.log("API response received:", response.data);
      return response.data;
    } catch (error) {
      console.error("API Error:", error);
      throw new Error(`Failed to fetch boards: ${error}`);
    }
  },

  getBoard: async (boardId: number): Promise<Board> => {
    try {
      console.log(
        "Making API request to:",
        `${API_BASE_URL}/boards/${boardId}`
      );
      const response = await api.get(`/boards/${boardId}`);
      console.log("API response received:", response.data);
      return response.data;
    } catch (error) {
      console.error("API Error:", error);
      throw new Error(`Failed to fetch board: ${error}`);
    }
  },

  createBoard: async (data: BoardCreate): Promise<Board> => {
    const response = await api.post("/boards", data);
    return response.data;
  },

  deleteBoard: async (boardId: number): Promise<void> => {
    await api.delete(`/boards/${boardId}`);
  },

  // Lists
  createList: async (data: ListCreate): Promise<TaskList> => {
    const response = await api.post("/lists", data);
    return response.data;
  },

  deleteList: async (listId: number): Promise<void> => {
    await api.delete(`/lists/${listId}`);
  },

  // Cards
  createCard: async (data: CardCreate): Promise<Card> => {
    const response = await api.post("/cards", data);
    return response.data;
  },

  moveCard: async (
    cardId: number,
    newListId: number,
    newPosition: number
  ): Promise<Card> => {
    const response = await api.put(`/cards/${cardId}/move`, {
      new_list_id: newListId,
      new_position: newPosition,
    });
    return response.data;
  },

  deleteCard: async (cardId: number): Promise<void> => {
    await api.delete(`/cards/${cardId}`);
  },
};

export const authService = {
  getToken: () => localStorage.getItem("access_token"),
  setToken: (token: string) => localStorage.setItem("access_token", token),
  removeToken: () => localStorage.removeItem("access_token"),
  isAuthenticated: () => !!localStorage.getItem("access_token"),
};
