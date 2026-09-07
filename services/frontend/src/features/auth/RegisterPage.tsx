import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAppDispatch } from "../../app/hooks";
import { register } from "./authSlice";

export default function RegisterPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(false);
    setSubmitting(true);
    const form = new FormData(event.currentTarget);

    try {
      await dispatch(
        register({
          email: String(form.get("email")),
          password: String(form.get("password")),
        }),
      ).unwrap();
      navigate("/", { replace: true });
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack component="form" spacing={3} onSubmit={handleSubmit}>
      <Typography component="h2" variant="h4">
        Create account
      </Typography>
      {error && <Alert severity="error">Unable to create account.</Alert>}
      <TextField
        autoComplete="email"
        label="Email"
        name="email"
        required
        type="email"
      />
      <TextField
        autoComplete="new-password"
        helperText="Use at least 8 characters."
        inputProps={{ minLength: 8 }}
        label="Password"
        name="password"
        required
        type="password"
      />
      <Button disabled={submitting} type="submit" variant="contained">
        Create account
      </Button>
      <Typography>
        Already registered? <Link to="/login">Sign in</Link>
      </Typography>
    </Stack>
  );
}
