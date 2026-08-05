import api from "./axios";

// department_id ya da en az 2 karakterlik search zorunlu, ikisi de yoksa 422.
export const getCourses = (params) => api.get("/courses", { params });
