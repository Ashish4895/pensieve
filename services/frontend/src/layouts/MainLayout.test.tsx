import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import authReducer from "../features/auth/authSlice";
import chatReducer from "../features/chat/chatSlice";
import notificationsReducer from "../features/notifications/notificationsSlice";
import MainLayout from "./MainLayout";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("MainLayout", () => {
  it("renders the shell and only marks the current navigation item active", () => {
    vi.stubGlobal(
      "WebSocket",
      class {
        readyState = 0;
        onopen: ((ev: Event) => void) | null = null;
        onclose: ((ev: CloseEvent) => void) | null = null;
        onerror: ((ev: Event) => void) | null = null;
        constructor(_url: string) {}
        send() {}
        close() {}
      },
    );

    const store = configureStore({
      reducer: {
        auth: authReducer,
        chat: chatReducer,
        notifications: notificationsReducer,
      },
      preloadedState: {
        auth: { access: "access-token", user: null, status: "idle" as const },
      },
    });
    const router = createMemoryRouter(
      [
        {
          element: <MainLayout />,
          children: [
            { path: "/", element: <h1>Chat page</h1> },
            {
              path: "/notifications",
              element: <h1>Notifications page</h1>,
            },
          ],
        },
      ],
      { initialEntries: ["/notifications"] },
    );

    render(
      <Provider store={store}>
        <RouterProvider router={router} />
      </Provider>,
    );

    expect(screen.getByText("Connecting…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Chat settings" })).toBeEnabled();
    expect(screen.getByRole("link", { name: "Chat" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(
      screen.getByRole("link", { name: "Notifications" }),
    ).toHaveAttribute("aria-current", "page");
  });
});
