import { useEffect } from "react";
import { useDispatch } from "react-redux";

import authService from "./services/authService";
import AppRoutes from "./routes/AppRoutes";
import { logout, restoreSession, setError, setLoading } from "./store/slices/authSlice";
import { CopilotProvider } from "./context/CopilotContext";

function App() {
  const dispatch = useDispatch();

  useEffect(() => {
    const storedToken = localStorage.getItem("token");

    if (!storedToken) {
      return;
    }

    let isMounted = true;

    const restoreAuthSession = async () => {
      dispatch(setLoading(true));

      try {
        const user = await authService.getCurrentUser();

        if (isMounted) {
          dispatch(restoreSession({ token: storedToken, user }));
        }
      } catch (error) {
        if (isMounted) {
          dispatch(logout());
          dispatch(setError(error?.userMessage || error?.response?.data?.detail || "Your session has expired. Please sign in again."));
        }
      } finally {
        if (isMounted) {
          dispatch(setLoading(false));
        }
      }
    };

    restoreAuthSession();

    return () => {
      isMounted = false;
    };
  }, [dispatch]);

  return (
    <CopilotProvider>
      <AppRoutes />
    </CopilotProvider>
  );
}

export default App;