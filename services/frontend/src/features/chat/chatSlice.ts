import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import { logout } from "../auth/authSlice";
import type { ChatSource } from "./chatApi";

export interface ChatMessage {
  id: string;
  role: "user" | "model";
  content: string;
  sources?: ChatSource[];
}

interface ChatState {
  messages: ChatMessage[];
}

const initialState: ChatState = { messages: [] };

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload);
    },
    clearMessages: (state) => {
      state.messages = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(logout.fulfilled, (state) => {
      state.messages = [];
    });
  },
});

export const { addMessage, clearMessages } = chatSlice.actions;
export default chatSlice.reducer;
