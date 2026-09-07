import { createBrowserRouter, Navigate } from "react-router-dom";

import LoginPage from "../features/auth/LoginPage";
import RegisterPage from "../features/auth/RegisterPage";
import ChatPage from "../features/chat/ChatPage";
import NotificationsPage from "../features/notifications/NotificationsPage";
import AuthLayout from "../layouts/AuthLayout";
import MainLayout from "../layouts/MainLayout";
import ProtectedRoute from "../routes/ProtectedRoute";

export const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <MainLayout />,
        children: [
          { path: "/", element: <ChatPage /> },
          {
            path: "/notifications",
            element: <NotificationsPage />,
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
