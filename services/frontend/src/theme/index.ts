import { alpha, createTheme } from "@mui/material/styles";

const accent = "#8b5cf6";

export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: accent,
      light: "#a78bfa",
    },
    secondary: {
      main: "#3b82f6",
    },
    background: {
      default: "#07050f",
      paper: "#16112d",
    },
    text: {
      primary: "#f3f1f9",
      secondary: "#a49fc6",
    },
    divider: "rgba(255, 255, 255, 0.08)",
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: "Inter, system-ui, sans-serif",
    h1: { fontFamily: "Outfit, Inter, system-ui, sans-serif" },
    h2: { fontFamily: "Outfit, Inter, system-ui, sans-serif" },
    h3: { fontFamily: "Outfit, Inter, system-ui, sans-serif" },
    h4: { fontFamily: "Outfit, Inter, system-ui, sans-serif" },
    h5: { fontFamily: "Outfit, Inter, system-ui, sans-serif" },
    h6: { fontFamily: "Outfit, Inter, system-ui, sans-serif" },
    button: {
      textTransform: "none",
      fontWeight: 600,
    },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: "var(--glass)",
          backgroundImage: "none",
          borderBottom: "1px solid var(--border)",
          boxShadow: "0 14px 40px rgba(0, 0, 0, 0.24)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
        },
        containedPrimary: {
          background: "linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)",
          boxShadow: `0 4px 14px ${alpha(accent, 0.3)}`,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: "#0f0b20",
        },
      },
    },
  },
});
