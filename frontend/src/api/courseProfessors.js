import api from "./axios";

// course_id zorunlu.
export const getCourseProfessors = ({ course_id, term, limit, offset } = {}) =>
    api.get("/course-professors", { params: { course_id, term, limit, offset } });

export const getCourseProfessor = (id) => api.get(`/course-professors/${id}`);
