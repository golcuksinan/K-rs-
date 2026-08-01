import api from "./axios";


export const getProfessors = () => {

    return api.get("/professors");

};


export const getProfessor = (id) => {

    return api.get(`/professors/${id}`);

};