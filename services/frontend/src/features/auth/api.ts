import { apiClient } from "../../lib/apiClient";

export interface User {
  id: number;
  email: string;
  role: string;
}

export interface Credentials {
  email: string;
  password: string;
}

export interface AuthData {
  access: string;
  user: User;
}

const jsonRequest = (body?: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const authApi = {
  login: (credentials: Credentials) =>
    apiClient<AuthData>("/auth/login/", jsonRequest(credentials)),
  register: (credentials: Credentials) =>
    apiClient<AuthData>("/auth/register/", jsonRequest(credentials)),
  refresh: () =>
    apiClient<Pick<AuthData, "access">>("/auth/refresh/", jsonRequest()),
  logout: () => apiClient<null>("/auth/logout/", jsonRequest()),
  me: () => apiClient<User>("/auth/me/"),
};
