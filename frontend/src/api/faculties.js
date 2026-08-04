import api from "./axios";


export const getFaculties=()=>{

    return api.get("/faculties");

};