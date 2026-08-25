import api from "./api";

export const doctorService = {
  async getAll() {
    const response = await api.get("/hcps");
    return response.data;
  },

  async getById(id) {
    const response = await api.get(`/hcps/${id}`);
    return response.data;
  },

  async create(data) {
    const response = await api.post("/hcps", data);
    return response.data;
  },

  async update(id, data) {
    const response = await api.put(`/hcps/${id}`, data);
    return response.data;
  },

  async delete(id) {
    const response = await api.delete(`/hcps/${id}`);
    return response.data;
  },
};

export default doctorService;
