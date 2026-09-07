import { CircularProgress, Stack } from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { RouterProvider } from "react-router-dom";

import { useAppDispatch } from "./app/hooks";
import { router } from "./app/router";
import {
  clearSession,
  loadMe,
  refreshSession,
} from "./features/auth/authSlice";

function App() {
  const dispatch = useAppDispatch();
  const booted = useRef(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (booted.current) return;
    booted.current = true;

    dispatch(refreshSession())
      .unwrap()
      .then(() => dispatch(loadMe()).unwrap())
      .catch(() => dispatch(clearSession()))
      .finally(() => setReady(true));
  }, [dispatch]);

  if (!ready) {
    return (
      <Stack alignItems="center" justifyContent="center" minHeight="100vh">
        <CircularProgress aria-label="Loading Pensieve" />
      </Stack>
    );
  }

  return <RouterProvider router={router} />;
}

export default App;
