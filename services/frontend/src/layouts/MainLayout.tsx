import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import {
  AppBar,
  Box,
  Button,
  Container,
  IconButton,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAppDispatch, useAppSelector } from "../app/hooks";
import { logout } from "../features/auth/authSlice";
import { clearByok } from "../features/chat/byok";
import { clearMessages } from "../features/chat/chatSlice";
import { createChatSocket, sendPing } from "../features/chat/wsClient";

export default function MainLayout() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const access = useAppSelector((state) => state.auth.access);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [live, setLive] = useState(false);

  useEffect(() => {
    if (!access) {
      setLive(false);
      return;
    }

    let cancelled = false;
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;

    const connect = () => {
      if (cancelled) return;
      socket = createChatSocket(access);
      socket.onopen = () => {
        attempt = 0;
        setLive(true);
        if (socket) sendPing(socket);
      };
      socket.onclose = () => {
        setLive(false);
        if (cancelled) return;
        const delay = Math.min(1000 * 2 ** attempt, 15_000);
        attempt += 1;
        retryTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      socket?.close();
      setLive(false);
    };
  }, [access]);

  const handleLogout = async () => {
    await dispatch(logout());
    clearByok();
    dispatch(clearMessages());
    navigate("/login", { replace: true });
  };

  return (
    <>
      <AppBar position="sticky" color="transparent">
        <Toolbar
          sx={{
            gap: { xs: 1, sm: 2 },
            minHeight: 72,
            py: 1,
            flexWrap: "wrap",
          }}
        >
          <Stack sx={{ flexGrow: 1, minWidth: { xs: "100%", sm: 0 } }}>
            <Typography variant="h6" fontWeight={700} lineHeight={1.2}>
              Pensieve
            </Typography>
            <Stack direction="row" spacing={0.75} alignItems="center">
              <Box
                aria-hidden
                sx={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  bgcolor: live ? "success.main" : "warning.main",
                  boxShadow: live
                    ? "0 0 8px rgba(16, 185, 129, 0.8)"
                    : "none",
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {live ? "Live" : "Connecting…"}
              </Typography>
            </Stack>
          </Stack>
          <Button color="inherit" component={NavLink} to="/" end>
            Chat
          </Button>
          <Button color="inherit" component={NavLink} to="/notifications">
            Notifications
          </Button>
          <IconButton
            color="inherit"
            aria-label="Chat settings"
            aria-expanded={settingsOpen}
            onClick={() => {
              setSettingsOpen(true);
              navigate("/");
            }}
          >
            <SettingsOutlinedIcon />
          </IconButton>
          <Button color="inherit" onClick={handleLogout}>
            Log out
          </Button>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ py: { xs: 2, sm: 4 } }}>
        <Container
          sx={{
            p: { xs: 2, sm: 3 },
            minHeight: "calc(100vh - 104px)",
            border: "1px solid var(--border)",
            borderRadius: 3,
            background: "var(--glass-subtle)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            boxShadow: "0 20px 50px rgba(0, 0, 0, 0.28)",
          }}
        >
          <Outlet
            context={{
              settingsOpen,
              closeSettings: () => setSettingsOpen(false),
            }}
          />
        </Container>
      </Box>
    </>
  );
}
