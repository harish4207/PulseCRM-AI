import api from "./axios";

export const loginUser = async (email, password) => {
    const response = await api.post("/login", {
        email,
        password,
    });

    return response.data;
};