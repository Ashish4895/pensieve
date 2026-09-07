import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAppSelector } from "../app/hooks";

export default function ProtectedRoute() {
  const access = useAppSelector((state) => state.auth.access);
  const location = useLocation();

  return access ? (
    <Outlet />
  ) : (
    <Navigate to="/login" replace state={{ from: location }} />
  );
}
