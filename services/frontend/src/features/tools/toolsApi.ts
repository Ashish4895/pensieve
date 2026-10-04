import { apiClient } from "../../lib/apiClient";

export interface McpServer {
  id: number;
  name: string;
  transport: string;
  command: string;
  args: string[];
  has_env: boolean;
  enabled: boolean;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
}

export interface ToolDefinition {
  id: number;
  name: string;
  title: string;
  description: string;
  input_schema: Record<string, unknown>;
  annotations: Record<string, unknown>;
  enabled: boolean;
  server_name: string;
  mcp_server: number;
  preference_enabled: boolean;
  updated_at: string;
}

export interface CreateServerPayload {
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
  enabled?: boolean;
}

export const toolsApi = {
  listServers: () =>
    apiClient<{ results: McpServer[] }>("/tools/servers/"),
  createServer: (payload: CreateServerPayload) =>
    apiClient<McpServer>("/tools/servers/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  patchServer: (id: number, payload: Partial<CreateServerPayload>) =>
    apiClient<McpServer>(`/tools/servers/${id}/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  deleteServer: (id: number) =>
    apiClient<null>(`/tools/servers/${id}/`, { method: "DELETE" }),
  discover: (id: number) =>
    apiClient<{ count: number; tools: ToolDefinition[] }>(
      `/tools/servers/${id}/discover/`,
      { method: "POST" },
    ),
  listTools: () => apiClient<{ results: ToolDefinition[] }>("/tools/"),
  setPreference: (toolId: number, enabled: boolean) =>
    apiClient<{ tool_id: number; enabled: boolean }>(
      `/tools/${toolId}/preference/`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      },
    ),
};
