import api from "./api";

const persistToken = (token) => {
  if (token) {
    localStorage.setItem("token", token);
  }
};

const clearToken = () => {
  localStorage.removeItem("token");
};

export const authService = {
  async register(payload) {
    return api.post("/register", payload);
  },

  async login(payload) {
    const response = await api.post("/login", payload);
    const token = response?.data?.access_token;

    if (token) {
      persistToken(token);
    }

    return response.data;
  },

  async getCurrentUser() {
    const response = await api.get("/me");
    return response.data;
  },

  clearSession() {
    clearToken();
  },
};

export default authService;
