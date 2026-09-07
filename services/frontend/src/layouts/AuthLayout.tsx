import { Box, Container, Paper, Typography } from "@mui/material";
import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <Box
      component="main"
      sx={{
        alignItems: "center",
        background: "linear-gradient(135deg, #312e81, #7c3aed)",
        display: "flex",
        minHeight: "100vh",
        py: 4,
      }}
    >
      <Container maxWidth="sm">
        <Typography
          component="h1"
          variant="h2"
          color="white"
          fontWeight={700}
          textAlign="center"
          gutterBottom
        >
          Pensieve
        </Typography>
        <Typography color="grey.200" textAlign="center" sx={{ mb: 4 }}>
          A place for your knowledge to grow.
        </Typography>
        <Paper elevation={8} sx={{ p: { xs: 3, sm: 5 } }}>
          <Outlet />
        </Paper>
      </Container>
    </Box>
  );
}
