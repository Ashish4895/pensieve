import { configureStore } from "@reduxjs/toolkit";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import {
  createMemoryRouter,
  RouterProvider,
} from "react-router-dom";
import { describe, expect, it } from "vitest";

import authReducer from "../features/auth/authSlice";
import ProtectedRoute from "./ProtectedRoute";

const renderRoute = (access: string | null) => {
  const store = configureStore({
    reducer: { auth: authReducer },
    preloadedState: {
      auth: { access, user: null, status: "idle" as const },
    },
  });
  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [{ path: "/", element: <h1>Private</h1> }],
      },
      {
        path: "/login",
        element: <h1>Login</h1>,
      },
    ],
    { initialEntries: ["/"] },
  );

  render(
    <Provider store={store}>
      <RouterProvider router={router} />
    </Provider>,
  );
};

describe("ProtectedRoute", () => {
  it("redirects logged-out users to login", async () => {
    renderRoute(null);

    expect(
      await screen.findByRole("heading", { name: "Login" }),
    ).toBeInTheDocument();
  });

  it("renders protected content for authenticated users", async () => {
    renderRoute("access-token");

    expect(
      await screen.findByRole("heading", { name: "Private" }),
    ).toBeInTheDocument();
  });
});
