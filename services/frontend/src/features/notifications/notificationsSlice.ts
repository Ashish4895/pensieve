import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";

import { logout } from "../auth/authSlice";
import {
  notificationsApi,
  type NotificationItem,
} from "./notificationsApi";

type LoadStatus = "idle" | "loading" | "succeeded" | "failed";

interface NotificationsState {
  items: NotificationItem[];
  status: LoadStatus;
  error: string | null;
  lastEventId: string;
}

const initialState: NotificationsState = {
  items: [],
  status: "idle",
  error: null,
  lastEventId: "",
};

export const fetchNotifications = createAsyncThunk(
  "notifications/fetch",
  notificationsApi.list,
);
export const markNotificationRead = createAsyncThunk(
  "notifications/markRead",
  notificationsApi.markRead,
);

const notificationsSlice = createSlice({
  name: "notifications",
  initialState,
  reducers: {
    notificationReceived: (
      state,
      action: PayloadAction<{
        notification: NotificationItem;
        lastEventId: string;
      }>,
    ) => {
      const { notification, lastEventId } = action.payload;
      const index = state.items.findIndex(({ id }) => id === notification.id);
      if (index === -1) state.items.unshift(notification);
      else state.items[index] = notification;
      state.lastEventId = lastEventId;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchNotifications.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchNotifications.fulfilled, (state, action) => {
        state.items = action.payload;
        state.status = "succeeded";
      })
      .addCase(fetchNotifications.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message ?? "Unable to load notifications";
      })
      .addCase(markNotificationRead.fulfilled, (state, action) => {
        const index = state.items.findIndex(({ id }) => id === action.payload.id);
        if (index !== -1) state.items[index] = action.payload;
      })
      .addCase(logout.fulfilled, () => initialState);
  },
});

export const { notificationReceived } = notificationsSlice.actions;
export default notificationsSlice.reducer;
