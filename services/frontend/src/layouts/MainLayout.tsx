import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAppDispatch } from "../app/hooks";
import { logout } from "../features/auth/authSlice";

export default function MainLayout() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await dispatch(logout());
    navigate("/login", { replace: true });
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Pensieve
          </Typography>
          <Button color="inherit" component={NavLink} to="/">
            Chat
          </Button>
          <Button color="inherit" component={NavLink} to="/notifications">
            Notifications
          </Button>
          <Button color="inherit" onClick={handleLogout}>
            Log out
          </Button>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ py: 4 }}>
        <Container>
          <Outlet />
        </Container>
      </Box>
    </>
  );
}
