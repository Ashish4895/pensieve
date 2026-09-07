import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";

import { useAppDispatch, useAppSelector } from "../../app/hooks";
import {
  fetchNotifications,
  markNotificationRead,
  notificationReceived,
} from "./notificationsSlice";
import { connectNotificationStream } from "./sse";

export default function NotificationsPage() {
  const dispatch = useAppDispatch();
  const access = useAppSelector((state) => state.auth.access);
  const { items, status, error, lastEventId } = useAppSelector(
    (state) => state.notifications,
  );
  const initialEventId = useRef(lastEventId);
  const [streamError, setStreamError] = useState(false);

  useEffect(() => {
    void dispatch(fetchNotifications());
  }, [dispatch]);

  useEffect(() => {
    if (!access) return;

    const connection = connectNotificationStream({
      access,
      lastEventId: initialEventId.current,
      onEvent: (notification, eventId) => {
        initialEventId.current = eventId;
        dispatch(
          notificationReceived({ notification, lastEventId: eventId }),
        );
      },
      onError: () => setStreamError(true),
      onOpen: () => setStreamError(false),
    });

    return connection.close;
  }, [access, dispatch]);

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" fontWeight={700}>
          Notifications
        </Typography>
        <Typography color="text.secondary">
          Updates from your Pensieve workspace.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {streamError && (
        <Alert severity="warning">Live updates are reconnecting…</Alert>
      )}

      {status === "loading" && items.length === 0 ? (
        <Box sx={{ display: "grid", placeItems: "center", py: 8 }}>
          <CircularProgress aria-label="Loading notifications" />
        </Box>
      ) : items.length === 0 ? (
        <Typography color="text.secondary">No notifications yet.</Typography>
      ) : (
        <List disablePadding>
          {items.map((notification, index) => (
            <Box key={notification.id}>
              {index > 0 && <Divider />}
              <ListItem
                alignItems="flex-start"
                secondaryAction={
                  notification.read_at ? null : (
                    <Button
                      size="small"
                      onClick={() => {
                        void dispatch(markNotificationRead(notification.id));
                      }}
                    >
                      Mark read
                    </Button>
                  )
                }
                sx={{ pr: notification.read_at ? 2 : 12, py: 2 }}
              >
                <ListItemText
                  primary={
                    <Typography
                      fontWeight={notification.read_at ? 400 : 700}
                    >
                      {notification.title}
                    </Typography>
                  }
                  secondary={
                    <>
                      {notification.body && (
                        <Typography component="span" color="text.secondary">
                          {notification.body}
                        </Typography>
                      )}
                      <Typography
                        component="span"
                        display="block"
                        variant="caption"
                        color="text.secondary"
                        sx={{ mt: 0.5 }}
                      >
                        {new Date(notification.created_at).toLocaleString()}
                      </Typography>
                    </>
                  }
                />
              </ListItem>
            </Box>
          ))}
        </List>
      )}
    </Stack>
  );
}
