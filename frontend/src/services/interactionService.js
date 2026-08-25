import api from "./api";

export const interactionService = {
  async getAll() {
    const response = await api.get("/interactions");
    return response.data;
  },

  async getById(id) {
    const response = await api.get(`/interactions/${id}`);
    return response.data;
  },

  async create(data) {
    const response = await api.post("/interactions", data);
    return response.data;
  },
};

export default interactionService;
