import axios, { AxiosResponse } from "axios";
import {
  AuthResponse,
  Board,
  BoardCreate,
  BoardInvite,
  Card,
  CardCreate,
  CardUpdate,
  Invitation,
  InvitationResponse,
  ListCreate,
  LoginData,
  MoveCard,
  PasswordUpdate,
  RegisterData,
  TaskList,
  User,
  UserProfile,
  UserUpdate,
} from "../types";

// Use environment variable or fallback to current host with different port
const API_BASE_URL = process.env.REACT_APP_API_URL
  ? `${process.env.REACT_APP_API_URL}/api`
  : `${window.location.protocol}//${window.location.hostname}:8001/api`;
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

// Authentication API
export const authAPI = {
  login: (data: LoginData): Promise<AxiosResponse<AuthResponse>> =>
    api.post("/login", data),

  register: (data: RegisterData): Promise<AxiosResponse<User>> =>
    api.post("/register", data),

  getCurrentUser: (): Promise<AxiosResponse<UserProfile>> => api.get("/me"),

  updateProfile: (data: UserUpdate): Promise<AxiosResponse<UserProfile>> =>
    api.put("/me", data),

  updatePassword: (
    data: PasswordUpdate
  ): Promise<AxiosResponse<{ message: string }>> =>
    api.put("/me/password", data),
};

// Board API
export const boardAPI = {
  getBoards: (): Promise<AxiosResponse<Board[]>> => api.get("/boards"),

  getBoard: (id: number): Promise<AxiosResponse<Board>> =>
    api.get(`/boards/${id}`),

  createBoard: (data: BoardCreate): Promise<AxiosResponse<Board>> =>
    api.post("/boards", data),

  deleteBoard: (id: number): Promise<AxiosResponse<{ message: string }>> =>
    api.delete(`/boards/${id}`),

  inviteUser: (
    boardId: number,
    data: BoardInvite
  ): Promise<AxiosResponse<{ message: string }>> =>
    api.post(`/boards/${boardId}/invite`, data),
};

// Invitation API
export const invitationAPI = {
  getInvitations: (): Promise<AxiosResponse<Invitation[]>> =>
    api.get("/invitations"),

  respondToInvitation: (
    invitationId: number,
    response: InvitationResponse
  ): Promise<AxiosResponse<{ message: string }>> =>
    api.post(`/invitations/${invitationId}/respond`, response),
};

// List API
export const listAPI = {
  createList: (data: ListCreate): Promise<AxiosResponse<TaskList>> =>
    api.post("/lists", data),

  deleteList: (id: number): Promise<AxiosResponse<{ message: string }>> =>
    api.delete(`/lists/${id}`),
};

// Card API
export const cardAPI = {
  createCard: (data: CardCreate): Promise<AxiosResponse<Card>> =>
    api.post("/cards", data),

  updateCard: (id: number, data: CardUpdate): Promise<AxiosResponse<Card>> =>
    api.put(`/cards/${id}`, data),

  moveCard: (id: number, data: MoveCard): Promise<AxiosResponse<Card>> =>
    api.put(`/cards/${id}/move`, data),

  deleteCard: (id: number): Promise<AxiosResponse<{ message: string }>> =>
    api.delete(`/cards/${id}`),
};

// Helper function to set auth token
export const setAuthToken = (token: string | null) => {
  if (token) {
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
};

// Helper function to get auth token
export const getAuthToken = (): string | null => {
  return localStorage.getItem("access_token");
};

// Helper function to check if user is authenticated
export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};

export default api;
