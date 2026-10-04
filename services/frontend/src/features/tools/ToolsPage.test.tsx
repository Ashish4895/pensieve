import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { store } from "../../app/store";
import ToolsPage from "./ToolsPage";
import { toolsApi } from "./toolsApi";

vi.mock("./toolsApi", () => ({
  toolsApi: {
    listTools: vi.fn(),
    listServers: vi.fn(),
    setPreference: vi.fn(),
    createServer: vi.fn(),
    discover: vi.fn(),
    deleteServer: vi.fn(),
    patchServer: vi.fn(),
  },
}));

describe("ToolsPage", () => {
  beforeEach(() => {
    vi.mocked(toolsApi.listTools).mockResolvedValue({
      results: [
        {
          id: 1,
          name: "pensieve_search_documents",
          title: "Search documents",
          description: "Search corpus",
          input_schema: {},
          annotations: {},
          enabled: true,
          server_name: "pensieve_mcp",
          mcp_server: 1,
          preference_enabled: true,
          updated_at: "2026-09-28T00:00:00Z",
        },
      ],
    });
    vi.mocked(toolsApi.listServers).mockResolvedValue({ results: [] });
  });

  it("toggles tool preference", async () => {
    const user = userEvent.setup();
    vi.mocked(toolsApi.setPreference).mockResolvedValue({
      tool_id: 1,
      enabled: false,
    });

    // Seed auth user as regular user (no server CRUD)
    store.dispatch({
      type: "auth/loadMe/fulfilled",
      payload: { id: 1, email: "u@example.com", role: "user" },
    });

    render(
      <Provider store={store}>
        <ToolsPage />
      </Provider>,
    );

    expect(
      await screen.findByText("Search documents"),
    ).toBeInTheDocument();

    const toggle = screen.getByLabelText(/Enable pensieve_search_documents/i);
    await user.click(toggle);
    expect(toolsApi.setPreference).toHaveBeenCalledWith(1, false);
  });
});
