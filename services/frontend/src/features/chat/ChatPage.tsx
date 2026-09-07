import {
  Alert,
  Box,
  Button,
  Drawer,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { type FormEvent, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { chatApi } from "./chatApi";
import { addMessage, clearMessages } from "./chatSlice";
import { DEFAULT_MODELS, loadByok, saveByok } from "./byok";

interface ChatLayoutContext {
  settingsOpen: boolean;
  closeSettings: () => void;
}

export default function ChatPage() {
  const dispatch = useAppDispatch();
  const messages = useAppSelector((state) => state.chat.messages);
  const { settingsOpen, closeSettings } = useOutletContext<ChatLayoutContext>();
  const [settings, setSettings] = useState(loadByok);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => saveByok(settings), [settings]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const text = message.trim();
    if (!text || !settings.apiKey.trim() || sending) return;

    setMessage("");
    setError("");
    setSending(true);
    dispatch(
      addMessage({ id: crypto.randomUUID(), role: "user", content: text }),
    );

    try {
      const result = await chatApi.sendMessage({ message: text });
      dispatch(
        addMessage({
          id: crypto.randomUUID(),
          role: "model",
          content: result.response,
          sources: result.sources,
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to send message");
    } finally {
      setSending(false);
    }
  };

  const handleClear = async () => {
    setError("");
    try {
      await chatApi.clearSession();
      dispatch(clearMessages());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to clear chat");
    }
  };

  return (
    <Stack spacing={2} sx={{ minHeight: "calc(100vh - 170px)" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="h4">Chat</Typography>
        <Button
          color="secondary"
          onClick={handleClear}
          disabled={sending || !settings.apiKey.trim()}
        >
          Clear session
        </Button>
      </Stack>

      {!settings.apiKey.trim() && (
        <Alert severity="info">Add an API key in Chat settings to begin.</Alert>
      )}
      {error && <Alert severity="error">{error}</Alert>}

      <Stack spacing={1.5} sx={{ flexGrow: 1 }}>
        {messages.length === 0 ? (
          <Box sx={{ m: "auto", textAlign: "center", color: "text.secondary" }}>
            <Typography variant="h6">What would you like to know?</Typography>
            <Typography variant="body2">
              Your provider key stays in this browser tab.
            </Typography>
          </Box>
        ) : (
          messages.map((item) => (
            <Stack
              key={item.id}
              alignItems={item.role === "user" ? "flex-end" : "flex-start"}
            >
              <Paper
                sx={{
                  p: 1.5,
                  maxWidth: "80%",
                  whiteSpace: "pre-wrap",
                  bgcolor:
                    item.role === "user" ? "primary.main" : "background.paper",
                  color:
                    item.role === "user"
                      ? "primary.contrastText"
                      : "text.primary",
                }}
              >
                {item.content}
              </Paper>
              {item.sources && item.sources.length > 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                  Sources:{" "}
                  {item.sources
                    .map((source) => source.source || "Unknown source")
                    .join(", ")}
                </Typography>
              )}
            </Stack>
          ))
        )}
      </Stack>

      <Box component="form" onSubmit={handleSubmit}>
        <Stack direction="row" spacing={1}>
          <TextField
            fullWidth
            label="Message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={!message.trim() || !settings.apiKey.trim() || sending}
          >
            {sending ? "Sending…" : "Send"}
          </Button>
        </Stack>
      </Box>

      <Drawer anchor="right" open={settingsOpen} onClose={closeSettings}>
        <Stack spacing={2.5} sx={{ width: { xs: 300, sm: 380 }, p: 3 }}>
          <Typography variant="h5">Chat settings</Typography>
          <FormControl fullWidth>
            <InputLabel id="provider-label">Provider</InputLabel>
            <Select
              labelId="provider-label"
              label="Provider"
              value={settings.provider}
              onChange={(event) => {
                const provider = event.target.value;
                setSettings((current) => ({
                  ...current,
                  provider,
                  model: DEFAULT_MODELS[provider] || "",
                }));
              }}
            >
              <MenuItem value="gemini">Gemini</MenuItem>
              <MenuItem value="openai">OpenAI</MenuItem>
              <MenuItem value="openrouter">OpenRouter</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="API key"
            type="password"
            value={settings.apiKey}
            onChange={(event) =>
              setSettings((current) => ({
                ...current,
                apiKey: event.target.value,
              }))
            }
            autoComplete="off"
          />
          <TextField
            label="Model"
            value={settings.model}
            onChange={(event) =>
              setSettings((current) => ({
                ...current,
                model: event.target.value,
              }))
            }
          />
          <Typography variant="caption" color="text.secondary">
            These settings are stored only in sessionStorage and disappear when
            this tab session ends.
          </Typography>
          <Button variant="contained" onClick={closeSettings}>
            Done
          </Button>
        </Stack>
      </Drawer>
    </Stack>
  );
}
