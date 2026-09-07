import { apiClient } from "../../lib/apiClient";

export interface NotificationItem {
  id: number;
  title: string;
  body: string;
  kind: string;
  created_at: string;
  read_at: string | null;
}

export const notificationsApi = {
  list: () =>
    apiClient<{ results: NotificationItem[] }>("/notifications/").then(
      ({ results }) => results,
    ),
  markRead: (id: number) =>
    apiClient<NotificationItem>(`/notifications/${id}/read/`, {
      method: "POST",
    }),
};
