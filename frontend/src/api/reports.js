import api from "./axios";

export const createReport = (data) => api.post("/reports", data);

export const getMyReports = (params) => api.get("/reports/me", { params });
