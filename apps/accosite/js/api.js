/**
 * AccoSite Builder - API Client
 * Communicates with the FastAPI backend.
 */
const API_BASE = '/api/v1/accosite';

function getToken() {
    return localStorage.getItem('accosite_token') || 'test-chris';
}

const headers = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`,
});

const api = {
    // ─── Projects ───────────────────────────────────────────────────────

    async listProjects() {
        const res = await fetch(`${API_BASE}/projects`, { headers: headers() });
        return res.json();
    },

    async createProject(name) {
        const res = await fetch(`${API_BASE}/projects`, {
            method: 'POST',
            headers: headers(),
            body: JSON.stringify({ name }),
        });
        return res.json();
    },

    async getProject(id) {
        const res = await fetch(`${API_BASE}/projects/${id}`, { headers: headers() });
        if (!res.ok) throw new Error('Project not found');
        return res.json();
    },

    async deleteProject(id) {
        await fetch(`${API_BASE}/projects/${id}`, {
            method: 'DELETE',
            headers: headers(),
        });
    },

    // ─── Sections ───────────────────────────────────────────────────────

    async saveSection(projectId, section, data) {
        const res = await fetch(`${API_BASE}/projects/${projectId}/section/${section}`, {
            method: 'PUT',
            headers: headers(),
            body: JSON.stringify({ data }),
        });
        return res.json();
    },

    async updateStep(projectId, step, completed = true) {
        const res = await fetch(`${API_BASE}/projects/${projectId}/step`, {
            method: 'PUT',
            headers: headers(),
            body: JSON.stringify({ step, completed }),
        });
        return res.json();
    },

    // ─── AI Generation ──────────────────────────────────────────────────

    async generateText(projectId, field, categoryId = null) {
        const body = { field };
        if (categoryId) body.category_id = categoryId;
        const res = await fetch(`${API_BASE}/projects/${projectId}/generate`, {
            method: 'POST',
            headers: headers(),
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Generation failed');
        }
        return res.json();
    },

    // ─── Images ─────────────────────────────────────────────────────────

    async uploadImage(projectId, file, label = 'general') {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(
            `${API_BASE}/projects/${projectId}/images?label=${encodeURIComponent(label)}`,
            {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${getToken()}` },
                body: formData,
            }
        );
        return res.json();
    },

    async listImages(projectId) {
        const res = await fetch(`${API_BASE}/projects/${projectId}/images`, {
            headers: headers(),
        });
        return res.json();
    },

    // ─── Preview & Export ───────────────────────────────────────────────

    previewUrl(projectId) {
        return `${API_BASE}/projects/${projectId}/preview?token=${getToken()}`;
    },

    exportUrl(projectId) {
        return `${API_BASE}/projects/${projectId}/export`;
    },

    // ─── Static Data ────────────────────────────────────────────────────

    async getAmenities() {
        const res = await fetch(`${API_BASE}/amenities`, { headers: headers() });
        return res.json();
    },

    async getTemplates() {
        const res = await fetch(`${API_BASE}/templates`, { headers: headers() });
        return res.json();
    },
};
