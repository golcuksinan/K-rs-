import api from "./axios";

export const getProfessors = (params) => api.get("/professors", { params });

export const getProfessor = (id) => api.get(`/professors/${id}`);
