export interface Card {
  id: number;
  title: string;
  description?: string;
  list_id: number;
  position: number;
  checklist: string[];
}

export interface TaskList {
  id: number;
  title: string;
  position: number;
  cards: Card[];
}

export interface Board {
  id: number;
  title: string;
  lists: TaskList[];
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
