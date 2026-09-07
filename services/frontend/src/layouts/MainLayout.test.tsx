import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";

import authReducer from "../features/auth/authSlice";
import MainLayout from "./MainLayout";

describe("MainLayout", () => {
  it("renders the shell and only marks the current navigation item active", () => {
    const store = configureStore({
      reducer: { auth: authReducer },
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

    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Chat settings" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "Chat" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(
      screen.getByRole("link", { name: "Notifications" }),
    ).toHaveAttribute("aria-current", "page");
  });
});
