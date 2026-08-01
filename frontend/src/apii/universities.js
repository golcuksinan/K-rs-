import api from "./axios";


export const getUniversities=()=>{

    return api.get("/universities");

};