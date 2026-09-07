import { configureStore } from "@reduxjs/toolkit";

import authReducer from "../features/auth/authSlice";
import chatReducer from "../features/chat/chatSlice";
import notificationsReducer from "../features/notifications/notificationsSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    chat: chatReducer,
    notifications: notificationsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
