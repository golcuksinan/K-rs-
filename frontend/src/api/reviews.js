import api from "./axios";


export const getReviews = () => {

    return api.get("/reviews");

};


export const createReview = (data) => {

    return api.post("/reviews",data);

};