import api from "./axios";

export const getPendingReviews = (params) => api.get("/reviews/pending", { params });

// status: "approved" | "rejected"
export const setReviewStatus = (id, status) =>
    api.patch(`/reviews/${id}/status`, { status });

// Bekleyen düzenlemenin kararı; has_pending_edit false ise 400.
export const setReviewEditStatus = (id, status) =>
    api.patch(`/reviews/${id}/edit-status`, { status });

export const getPendingReports = (params) => api.get("/reports/pending", { params });

// status: "resolved" | "dismissed"
export const setReportStatus = (id, status) =>
    api.patch(`/reports/${id}/status`, { status });

// Bu iki uç Page zarfı kullanmaz.
export const getStats = () => api.get("/admin/stats");

export const getEventStats = (days) => api.get("/admin/stats/events", { params: { days } });
