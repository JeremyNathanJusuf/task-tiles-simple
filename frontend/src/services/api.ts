import axios from "axios";
import { Board, Card, TaskList } from "../types";

// Use the current host but different port for API
const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000/api`;
console.log("API_BASE_URL:", API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const apiService = {
  // Get the main board with all lists and cards
  getBoard: async (): Promise<Board> => {
    try {
      console.log("Making API request to:", `${API_BASE_URL}/board`);
      const response = await api.get("/board");
      console.log("API response received:", response.data);
      return response.data;
    } catch (error) {
      console.error("API Error:", error);
      throw new Error(`Failed to fetch board data: ${error}`);
    }
  },

  // Create a new list
  createList: async (title: string): Promise<TaskList> => {
    const response = await api.post("/lists", null, {
      params: { title },
    });
    return response.data;
  },

  // Create a new card
  createCard: async (
    title: string,
    description?: string,
    listId: number = 1
  ): Promise<Card> => {
    const response = await api.post("/cards", null, {
      params: {
        title,
        description: description || undefined,
        list_id: listId,
      },
    });
    return response.data;
  },

  // Move a card to a different list or position
  moveCard: async (
    cardId: number,
    newListId: number,
    newPosition: number
  ): Promise<Card> => {
    const response = await api.put(`/cards/${cardId}/move`, null, {
      params: {
        new_list_id: newListId,
        new_position: newPosition,
      },
    });
    return response.data;
  },
};
