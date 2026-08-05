import api from "./axios";

// status filtresi yalnızca admin token'ıyla çalışır, aksi halde 403.
export const getReviews = (params) => api.get("/reviews", { params });

export const getMyReviews = (params) => api.get("/reviews/me", { params });

export const createReview = (data) => api.post("/reviews", data);

export const updateReview = (id, data) => api.patch(`/reviews/${id}`, data);

export const deleteReview = (id) => api.delete(`/reviews/${id}`);
