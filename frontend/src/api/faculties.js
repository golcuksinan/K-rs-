import api from "./axios";

// university_id zorunlu; verilmezse backend 422 döner.
export const getFaculties = ({ university_id, search, limit, offset } = {}) =>
    api.get("/faculties", { params: { university_id, search, limit, offset } });
