import api from "./axios";


export const getCourses = () => {

    return api.get("/courses");

};


export const getCourse = (id) => {

    return api.get(`/courses/${id}`);

};