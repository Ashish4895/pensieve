import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { authApi } from "./api";
import type { Credentials, User } from "./api";

type AuthStatus = "idle" | "loading" | "succeeded" | "failed";

interface AuthState {
  access: string | null;
  user: User | null;
  status: AuthStatus;
}

const initialState: AuthState = {
  access: null,
  user: null,
  status: "idle",
};

export const login = createAsyncThunk("auth/login", authApi.login);
export const register = createAsyncThunk(
  "auth/register",
  (credentials: Credentials) => authApi.register(credentials),
);
export const logout = createAsyncThunk("auth/logout", authApi.logout);
export const refreshSession = createAsyncThunk(
  "auth/refreshSession",
  authApi.refresh,
);
export const loadMe = createAsyncThunk("auth/loadMe", authApi.me);

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(login.fulfilled, (state, action) => {
        state.access = action.payload.access;
        state.user = action.payload.user;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.access = action.payload.access;
        state.user = action.payload.user;
      })
      .addCase(refreshSession.fulfilled, (state, action) => {
        state.access = action.payload.access;
      })
      .addCase(loadMe.fulfilled, (state, action) => {
        state.user = action.payload;
      })
      .addCase(logout.fulfilled, (state) => {
        state.access = null;
        state.user = null;
      })
      .addMatcher(
        (action) =>
          action.type.startsWith("auth/") && action.type.endsWith("/pending"),
        (state) => {
          state.status = "loading";
        },
      )
      .addMatcher(
        (action) =>
          action.type.startsWith("auth/") && action.type.endsWith("/fulfilled"),
        (state) => {
          state.status = "succeeded";
        },
      )
      .addMatcher(
        (action) =>
          action.type.startsWith("auth/") && action.type.endsWith("/rejected"),
        (state) => {
          state.status = "failed";
        },
      );
  },
});

export default authSlice.reducer;
