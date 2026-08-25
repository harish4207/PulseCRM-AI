import axios from "axios";

export const getReadableApiError = (error) => {
  const data = error?.response?.data;
  const detail = typeof data === "string" ? data : data?.detail || data?.message || data?.error;

  if (error?.code === "ERR_NETWORK" || !error?.response) {
    return "The server is currently unavailable. Please try again in a moment.";
  }

  switch (error.response.status) {
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You do not have permission to perform this action.";
    case 404:
      return "The requested resource could not be found.";
    case 422:
      return detail || "Please review the form and try again.";
    case 429:
      return "Too many requests were sent. Please wait a moment and retry.";
    case 500:
      return "The server encountered an error. Please try again later.";
    default:
      return detail || "Something went wrong. Please try again.";
  }
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");

  if (token) {
    // Ensure headers object exists and attach the Bearer token without template literals
    config.headers = config.headers || {};
    config.headers.Authorization = 'Bearer ' + token;
  } else {
    if (config.headers) delete config.headers.Authorization;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("token");
    }

    return Promise.reject({
      ...error,
      userMessage: getReadableApiError(error),
    });
  }
);

export default api;


