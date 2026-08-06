import api from "./axios";

// faculty_id verilirse düz liste, verilmezse ada göre gruplanmış liste döner.
export const getDepartments = (params) => api.get("/departments", { params });
