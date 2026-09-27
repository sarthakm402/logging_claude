const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path) {
    const response = await fetch(`${API_BASE}${path}`);

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }

    return response.json();
}

export async function getProjects() {
    return request("/api/projects");
}

export async function getDashboardSummary() {
    return request("/api/dashboard/summary");
}

export async function getDashboardTokens() {
    return request("/api/dashboard/tokens");
}

export async function getDashboardCost() {
    return request("/api/dashboard/cost");
}

export async function getDashboardModels() {
    return request("/api/dashboard/models");
}

export async function getDashboardUsers() {
    return request("/api/dashboard/users");
}

export async function getDashboardActivity() {
    return request("/api/dashboard/activity");
}

export async function getDashboardPerformance() {
    return request("/api/dashboard/performance");
}

export async function getProjectSummary(projectId) {
    return request(`/api/dashboard/projects/${projectId}/summary`);
}

export async function getProjectTokens(projectId) {
    return request(`/api/dashboard/projects/${projectId}/tokens`);
}

export async function getProjectCost(projectId) {
    return request(`/api/dashboard/projects/${projectId}/cost`);
}

export async function getProjectModels(projectId) {
    return request(`/api/dashboard/projects/${projectId}/models`);
}

export async function getProjectUsers(projectId) {
    return request(`/api/dashboard/projects/${projectId}/users`);
}

export async function getProjectActivity(projectId) {
    return request(`/api/dashboard/projects/${projectId}/activity`);
}

export async function getProjectPerformance(projectId) {
    return request(`/api/dashboard/projects/${projectId}/performance`);
}