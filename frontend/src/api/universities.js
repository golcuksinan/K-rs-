import api from "./axios";

export const getUniversities = (params) => api.get("/universities", { params });
