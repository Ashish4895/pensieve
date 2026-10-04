import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { useAppSelector } from "../../app/hooks";
import {
  toolsApi,
  type McpServer,
  type ToolDefinition,
} from "./toolsApi";

function parseArgs(raw: string): string[] {
  const trimmed = raw.trim();
  if (!trimmed) return [];
  try {
    const parsed = JSON.parse(trimmed);
    if (Array.isArray(parsed)) return parsed.map(String);
  } catch {
    /* fall through */
  }
  return trimmed.split(/\s+/).filter(Boolean);
}

function parseEnv(raw: string): Record<string, string> | undefined {
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  const env: Record<string, string> = {};
  for (const line of trimmed.split("\n")) {
    const idx = line.indexOf("=");
    if (idx <= 0) continue;
    env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return Object.keys(env).length ? env : undefined;
}

export default function ToolsPage() {
  const role = useAppSelector((state) => state.auth.user?.role ?? "user");
  const canManage = role === "admin" || role === "super_admin";

  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [servers, setServers] = useState<McpServer[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const [name, setName] = useState("");
  const [command, setCommand] = useState("");
  const [argsText, setArgsText] = useState("");
  const [envText, setEnvText] = useState("");

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const toolsData = await toolsApi.listTools();
      setTools(toolsData.results);
      if (canManage) {
        const serversData = await toolsApi.listServers();
        setServers(serversData.results);
      }
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Failed to load tools");
    }
  }, [canManage]);

  useEffect(() => {
    void load();
  }, [load]);

  const onToggle = async (tool: ToolDefinition, enabled: boolean) => {
    setBusyId(tool.id);
    try {
      await toolsApi.setPreference(tool.id, enabled);
      setTools((prev) =>
        prev.map((t) =>
          t.id === tool.id ? { ...t, preference_enabled: enabled } : t,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preference update failed");
    } finally {
      setBusyId(null);
    }
  };

  const onCreate = async () => {
    setError(null);
    try {
      await toolsApi.createServer({
        name: name.trim(),
        command: command.trim(),
        args: parseArgs(argsText),
        env: parseEnv(envText),
      });
      setName("");
      setCommand("");
      setArgsText("");
      setEnvText("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  };

  const onDiscover = async (serverId: number) => {
    setBusyId(serverId);
    setError(null);
    try {
      await toolsApi.discover(serverId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discover failed");
    } finally {
      setBusyId(null);
    }
  };

  const onDelete = async (serverId: number) => {
    setBusyId(serverId);
    try {
      await toolsApi.deleteServer(serverId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" fontWeight={700}>
          Tools
        </Typography>
        <Typography color="text.secondary">
          Enable MCP tools for chat. Admins can connect FastMCP / MCP stdio
          servers.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      {status === "loading" && tools.length === 0 ? (
        <Box sx={{ display: "grid", placeItems: "center", py: 8 }}>
          <CircularProgress aria-label="Loading tools" />
        </Box>
      ) : (
        <Stack spacing={1.5}>
          <Typography variant="h6">Available tools</Typography>
          {tools.length === 0 ? (
            <Typography color="text.secondary">
              No tools discovered yet.
            </Typography>
          ) : (
            tools.map((tool) => (
              <Stack
                key={tool.id}
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{
                  borderBottom: "1px solid var(--border)",
                  py: 1,
                }}
              >
                <Box>
                  <Typography fontWeight={600}>
                    {tool.title || tool.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {tool.server_name} · {tool.name}
                  </Typography>
                  {tool.description && (
                    <Typography variant="body2" color="text.secondary">
                      {tool.description}
                    </Typography>
                  )}
                </Box>
                <FormControlLabel
                  control={
                    <Switch
                      checked={tool.preference_enabled}
                      disabled={busyId === tool.id}
                      onChange={(_, checked) => void onToggle(tool, checked)}
                    />
                  }
                  label={tool.preference_enabled ? "On" : "Off"}
                  aria-label={`Enable ${tool.name}`}
                />
              </Stack>
            ))
          )}
        </Stack>
      )}

      {canManage && (
        <>
          <Divider />
          <Stack spacing={2}>
            <Typography variant="h6">MCP servers</Typography>
            {servers.map((server) => (
              <Stack
                key={server.id}
                direction={{ xs: "column", sm: "row" }}
                spacing={1}
                alignItems={{ sm: "center" }}
                justifyContent="space-between"
              >
                <Box>
                  <Typography fontWeight={600}>
                    {server.name}
                    {server.is_builtin ? " (builtin)" : ""}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {server.is_builtin
                      ? "pensieve_mcp via python -m tools.pensieve_mcp"
                      : `${server.command} ${(server.args || []).join(" ")}`}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={busyId === server.id}
                    onClick={() => void onDiscover(server.id)}
                  >
                    Discover
                  </Button>
                  {!server.is_builtin && (
                    <Button
                      size="small"
                      color="error"
                      disabled={busyId === server.id}
                      onClick={() => void onDelete(server.id)}
                    >
                      Delete
                    </Button>
                  )}
                </Stack>
              </Stack>
            ))}

            <Typography variant="subtitle1" fontWeight={600}>
              Add server
            </Typography>
            <TextField
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              size="small"
            />
            <TextField
              label="Command"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              size="small"
              placeholder="uv"
            />
            <TextField
              label="Args (JSON array or space-separated)"
              value={argsText}
              onChange={(e) => setArgsText(e.target.value)}
              size="small"
              placeholder='["run","weather.py"]'
            />
            <TextField
              label="Env (KEY=value per line)"
              value={envText}
              onChange={(e) => setEnvText(e.target.value)}
              size="small"
              multiline
              minRows={2}
            />
            <Box>
              <Button
                variant="contained"
                disabled={!name.trim() || !command.trim()}
                onClick={() => void onCreate()}
              >
                Add MCP server
              </Button>
            </Box>
          </Stack>
        </>
      )}
    </Stack>
  );
}
