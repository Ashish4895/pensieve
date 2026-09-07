import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAppDispatch } from "../../app/hooks";
import { login } from "./authSlice";

export default function LoginPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(false);
    setSubmitting(true);
    const form = new FormData(event.currentTarget);

    try {
      await dispatch(
        login({
          email: String(form.get("email")),
          password: String(form.get("password")),
        }),
      ).unwrap();
      const from = (location.state as { from?: { pathname?: string } } | null)
        ?.from?.pathname;
      navigate(from && from !== "/login" ? from : "/", { replace: true });
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack component="form" spacing={3} onSubmit={handleSubmit}>
      <Typography component="h2" variant="h4">
        Sign in
      </Typography>
      {error && <Alert severity="error">Unable to sign in.</Alert>}
      <TextField
        autoComplete="email"
        label="Email"
        name="email"
        required
        type="email"
      />
      <TextField
        autoComplete="current-password"
        label="Password"
        name="password"
        required
        type="password"
      />
      <Button disabled={submitting} type="submit" variant="contained">
        Sign in
      </Button>
      <Typography>
        New to Pensieve? <Link to="/register">Create an account</Link>
      </Typography>
    </Stack>
  );
}
