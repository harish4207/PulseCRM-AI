import { createSlice } from "@reduxjs/toolkit";

const getStoredToken = () => {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem("token");
};

const initialState = {
  token: getStoredToken(),
  user: null,
  isAuthenticated: Boolean(getStoredToken()),
  loading: false,
  error: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    loginSuccess: (state, action) => {
      const { token, user = null } = action.payload ?? {};

      state.token = token ?? state.token;
      state.user = user;
      state.isAuthenticated = Boolean(state.token);
      state.loading = false;
      state.error = null;

      if (state.token) {
        localStorage.setItem("token", state.token);
      } else {
        localStorage.removeItem("token");
      }
    },
    logout: (state) => {
      state.token = null;
      state.user = null;
      state.isAuthenticated = false;
      state.loading = false;
      state.error = null;
      localStorage.removeItem("token");
    },
    setLoading: (state, action) => {
      state.loading = Boolean(action.payload);
    },
    setError: (state, action) => {
      state.error = action.payload ?? null;
      state.loading = false;
    },
    restoreSession: (state, action) => {
      const { token, user = null } = action.payload ?? {};

      state.token = token ?? null;
      state.user = user;
      state.isAuthenticated = Boolean(token);
      state.loading = false;
      state.error = null;

      if (token) {
        localStorage.setItem("token", token);
      } else {
        localStorage.removeItem("token");
      }
    },
  },
});

export const { loginSuccess, logout, setLoading, setError, restoreSession } = authSlice.actions;

export default authSlice.reducer;
