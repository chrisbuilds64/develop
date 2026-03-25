/**
 * AccoSite Builder - Main Application
 * Alpine.js powered wizard application.
 */

document.addEventListener('alpine:init', () => {

    // ─── Main App Store ─────────────────────────────────────────────────
    Alpine.store('app', {
        view: 'login',      // login | home | wizard
        loggedIn: !!localStorage.getItem('accosite_token'),
        projectId: null,
        project: null,
        projects: [],
        loading: false,
        saving: false,
        generating: false,
        error: null,
        currentStep: 1,
        amenities: {},
        templates: [],

        async init() {
            if (localStorage.getItem('accosite_token')) {
                this.loggedIn = true;
                this.view = 'home';
                try {
                    this.amenities = await api.getAmenities();
                    this.templates = await api.getTemplates();
                    await this.loadProjects();
                } catch (e) {
                    console.error('Init failed:', e);
                }
            } else {
                this.view = 'login';
            }
        },

        login(email, password) {
            // Demo auth: any email + password "demo" works
            if (password === 'demo') {
                const token = 'demo-' + email.split('@')[0];
                localStorage.setItem('accosite_token', token);
                localStorage.setItem('accosite_email', email);
                this.loggedIn = true;
                this.view = 'home';
                this.init();
            } else {
                this.error = 'Invalid credentials. Use password: demo';
            }
        },

        logout() {
            localStorage.removeItem('accosite_token');
            localStorage.removeItem('accosite_email');
            this.loggedIn = false;
            this.view = 'login';
            this.projects = [];
            this.project = null;
            this.projectId = null;
        },

        async loadProjects() {
            this.loading = true;
            try {
                this.projects = await api.listProjects();
            } catch (e) {
                this.error = 'Failed to load projects';
            }
            this.loading = false;
        },

        async createProject(name) {
            this.loading = true;
            try {
                const result = await api.createProject(name);
                this.projectId = result.id;
                await this.loadProject(result.id);
                this.view = 'wizard';
                this.currentStep = 1;
            } catch (e) {
                this.error = 'Failed to create project';
            }
            this.loading = false;
        },

        async openProject(id) {
            this.loading = true;
            try {
                await this.loadProject(id);
                this.projectId = id;
                this.view = 'wizard';
                this.currentStep = this.project.current_step || 1;
            } catch (e) {
                this.error = 'Failed to open project';
            }
            this.loading = false;
        },

        async loadProject(id) {
            this.project = await api.getProject(id);
        },

        async deleteProject(id) {
            if (!confirm('Delete this project? This cannot be undone.')) return;
            await api.deleteProject(id);
            await this.loadProjects();
        },

        goHome() {
            this.view = 'home';
            this.projectId = null;
            this.project = null;
            this.loadProjects();
        },

        async saveSection(section, data) {
            this.saving = true;
            try {
                await api.saveSection(this.projectId, section, data);
                await this.loadProject(this.projectId);
            } catch (e) {
                this.error = 'Failed to save';
            }
            this.saving = false;
        },

        async goToStep(step) {
            // Save current step completion and reload project data
            await api.updateStep(this.projectId, this.currentStep, true);
            // Load fresh data, then switch step (triggers new component init)
            this.currentStep = 0; // briefly hide all steps
            await this.loadProject(this.projectId);
            await api.updateStep(this.projectId, step, false);
            // Small delay so Alpine picks up the new project data before init
            await new Promise(r => setTimeout(r, 50));
            this.currentStep = step;
        },

        async nextStep() {
            if (this.currentStep < 10) {
                await this.goToStep(this.currentStep + 1);
            }
        },

        async prevStep() {
            if (this.currentStep > 1) {
                await this.goToStep(this.currentStep - 1);
            }
        },

        async generateText(field, categoryId = null) {
            this.generating = true;
            this.error = null;
            try {
                const result = await api.generateText(this.projectId, field, categoryId);
                return result.text;
            } catch (e) {
                this.error = `AI generation failed: ${e.message}`;
                return null;
            } finally {
                this.generating = false;
            }
        },
    });
});


// ─── Step Components ────────────────────────────────────────────────────────

function stepPropertyInfo() {
    return {
        form: {},
        facilityImages: [],
        uploading: false,

        async init() {
            const defaults = {
                name: '', property_type: 'villa', stars: '', tagline: '',
                owner_name: '', email: '', phone: '', whatsapp: '',
                instagram: '', facebook: '', tripadvisor_url: '', google_reviews_url: '',
                check_in: '14:00', check_out: '11:00', year_founded: '',
                languages: ['en'], website_language: 'en',
                about: '', history: '', policies: '',
                images: [], hero_image: '',
            };
            const p = Alpine.store('app').project?.property_info || {};
            this.form = { ...defaults, ...p };
            // Build image list from saved filenames
            this.facilityImages = (this.form.images || []).map(f => ({ filename: f }));
        },

        async uploadImage(event) {
            const files = event.target.files;
            if (!files.length) return;
            this.uploading = true;
            const store = Alpine.store('app');
            for (const file of files) {
                try {
                    const result = await api.uploadImage(store.projectId, file, 'facility');
                    this.form.images.push(result.filename);
                    if (!this.form.hero_image) this.form.hero_image = result.filename;
                } catch (e) {
                    store.error = 'Upload failed: ' + e.message;
                }
            }
            await this.save();
            this.facilityImages = (this.form.images || []).map(f => ({ filename: f }));
            this.uploading = false;
            event.target.value = '';
        },

        setHero(filename) {
            this.form.hero_image = filename;
            this.save();
        },

        removeImage(filename) {
            this.form.images = this.form.images.filter(f => f !== filename);
            if (this.form.hero_image === filename) {
                this.form.hero_image = this.form.images[0] || '';
            }
            this.facilityImages = this.form.images.map(f => ({ filename: f }));
            this.save();
        },

        imageUrl(filename) {
            return `/api/v1/accosite/projects/${Alpine.store('app').projectId}/images/${filename}?token=${getToken()}`;
        },

        async save() {
            await Alpine.store('app').saveSection('property', this.form);
        },

        async generateField(field) {
            const text = await Alpine.store('app').generateText(field);
            if (text) {
                this.form[field] = text;
                await this.save();
            }
        },
    };
}

function stepRoomCategories() {
    return {
        categories: [],
        showForm: false,
        editIndex: -1,
        form: { id: '', name: '', units: 1, max_occupancy: 2, size_sqm: null, bed_type: '' },

        init() {
            this.categories = JSON.parse(JSON.stringify(
                Alpine.store('app').project?.room_categories || []
            ));
        },

        addCategory() {
            this.form = { id: '', name: '', units: 1, max_occupancy: 2, size_sqm: null, bed_type: '' };
            this.editIndex = -1;
            this.showForm = true;
        },

        editCategory(index) {
            this.form = { ...this.categories[index] };
            this.editIndex = index;
            this.showForm = true;
        },

        async saveCategory() {
            if (!this.form.name) return;
            if (!this.form.id) {
                this.form.id = this.form.name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
            }
            if (this.editIndex >= 0) {
                this.categories[this.editIndex] = { ...this.form };
            } else {
                this.categories.push({ ...this.form });
            }
            this.showForm = false;
            await Alpine.store('app').saveSection('rooms', this.categories);
        },

        async removeCategory(index) {
            this.categories.splice(index, 1);
            await Alpine.store('app').saveSection('rooms', this.categories);
        },
    };
}

function stepRoomDetails() {
    return {
        activeTab: 0,
        details: [],
        amenityGroups: {},
        uploading: false,

        init() {
            const project = Alpine.store('app').project;
            this.amenityGroups = Alpine.store('app').amenities;
            const categories = project?.room_categories || [];
            const existing = project?.room_details || [];

            this.details = categories.map(cat => {
                const found = existing.find(d => d.category_id === cat.id);
                return found ? { ...found, images: found.images || [] } : {
                    category_id: cat.id,
                    amenities: [],
                    custom_amenities: [],
                    short_description: '',
                    long_description: '',
                    images: [],
                    min_stay_nights: 1,
                };
            });
        },

        toggleAmenity(detailIdx, amenityId) {
            const d = this.details[detailIdx];
            const idx = d.amenities.indexOf(amenityId);
            if (idx >= 0) d.amenities.splice(idx, 1);
            else d.amenities.push(amenityId);
        },

        hasAmenity(detailIdx, amenityId) {
            return this.details[detailIdx]?.amenities?.includes(amenityId) || false;
        },

        async uploadRoomImage(event, detailIdx) {
            const files = event.target.files;
            if (!files.length) return;
            this.uploading = true;
            const store = Alpine.store('app');
            const catId = this.details[detailIdx].category_id;
            for (const file of files) {
                try {
                    const result = await api.uploadImage(store.projectId, file, 'room-' + catId);
                    this.details[detailIdx].images.push(result.filename);
                } catch (e) {
                    store.error = 'Upload failed: ' + e.message;
                }
            }
            await this.save();
            this.uploading = false;
            event.target.value = '';
        },

        removeRoomImage(detailIdx, filename) {
            this.details[detailIdx].images = this.details[detailIdx].images.filter(f => f !== filename);
            this.save();
        },

        imageUrl(filename) {
            return `/api/v1/accosite/projects/${Alpine.store('app').projectId}/images/${filename}?token=${getToken()}`;
        },

        async save() {
            await Alpine.store('app').saveSection('room_details', this.details);
        },

        async generateDescription(detailIdx, length) {
            const catId = this.details[detailIdx].category_id;
            const field = length === 'short' ? 'room_short' : 'room_long';
            const text = await Alpine.store('app').generateText(field, catId);
            if (text) {
                const key = length === 'short' ? 'short_description' : 'long_description';
                this.details[detailIdx][key] = text;
                await this.save();
            }
        },
    };
}

function stepPricing() {
    return {
        form: {},

        init() {
            const project = Alpine.store('app').project;
            const pricing = project?.pricing || {};
            const categories = project?.room_categories || [];

            this.form = {
                currency: pricing.currency || 'USD',
                currency_symbol: pricing.currency_symbol || '$',
                show_prices: pricing.show_prices !== false,
                pricing_note: pricing.pricing_note || '',
                taxes_included: pricing.taxes_included || false,
                tax_note: pricing.tax_note || '',
                seasons: pricing.seasons || [
                    { name: 'High Season', months: [7, 8, 12] },
                    { name: 'Low Season', months: [1, 2, 3, 4, 5, 6, 9, 10, 11] },
                ],
                categories: categories.map(cat => {
                    const existing = (pricing.categories || []).find(p => p.category_id === cat.id);
                    return existing || {
                        category_id: cat.id,
                        price_high: null,
                        price_low: null,
                        extra_person_fee: null,
                    };
                }),
            };
        },

        getCategoryName(catId) {
            const cats = Alpine.store('app').project?.room_categories || [];
            return cats.find(c => c.id === catId)?.name || catId;
        },

        async save() {
            await Alpine.store('app').saveSection('pricing', this.form);
        },
    };
}

function stepLocation() {
    return {
        form: {},

        init() {
            const loc = Alpine.store('app').project?.location || {};
            this.form = {
                address_line1: loc.address_line1 || '',
                address_line2: loc.address_line2 || '',
                city: loc.city || '',
                region: loc.region || '',
                country: loc.country || '',
                postal_code: loc.postal_code || '',
                latitude: loc.latitude || null,
                longitude: loc.longitude || null,
                google_maps_url: loc.google_maps_url || '',
                google_maps_embed_url: loc.google_maps_embed_url || '',
                about_location: loc.about_location || '',
                getting_here: loc.getting_here || '',
                nearby: loc.nearby || [],
            };
        },

        addNearby() {
            this.form.nearby.push({ name: '', distance: '', category: '' });
        },

        removeNearby(index) {
            this.form.nearby.splice(index, 1);
        },

        async save() {
            await Alpine.store('app').saveSection('location', this.form);
        },

        async generateField(field) {
            await this.save(); // Save current data first so AI has context
            const text = await Alpine.store('app').generateText(field);
            if (text) {
                if (field === 'location') this.form.about_location = text;
                else this.form.getting_here = text;
                await this.save();
            }
        },
    };
}

function stepReviews() {
    return {
        reviews: [],
        showForm: false,
        editIndex: -1,
        form: { author: '', country: '', rating: 5, text: '', date: '' },

        init() {
            this.reviews = JSON.parse(JSON.stringify(
                Alpine.store('app').project?.reviews || []
            ));
        },

        addReview() {
            this.form = { author: '', country: '', rating: 5, text: '', date: '' };
            this.editIndex = -1;
            this.showForm = true;
        },

        editReview(index) {
            this.form = { ...this.reviews[index] };
            this.editIndex = index;
            this.showForm = true;
        },

        async saveReview() {
            if (!this.form.author || !this.form.text) return;
            if (this.editIndex >= 0) {
                this.reviews[this.editIndex] = { ...this.form };
            } else {
                this.reviews.push({ ...this.form });
            }
            this.showForm = false;
            await Alpine.store('app').saveSection('reviews', this.reviews);
        },

        async removeReview(index) {
            this.reviews.splice(index, 1);
            await Alpine.store('app').saveSection('reviews', this.reviews);
        },
    };
}

function stepFaq() {
    return {
        entries: [],
        showForm: false,
        editIndex: -1,
        form: { question: '', answer: '' },

        init() {
            this.entries = JSON.parse(JSON.stringify(
                Alpine.store('app').project?.faq || []
            ));
        },

        addEntry() {
            this.form = { question: '', answer: '' };
            this.editIndex = -1;
            this.showForm = true;
        },

        editEntry(index) {
            this.form = { ...this.entries[index] };
            this.editIndex = index;
            this.showForm = true;
        },

        async saveEntry() {
            if (!this.form.question) return;
            if (this.editIndex >= 0) {
                this.entries[this.editIndex] = { ...this.form };
            } else {
                this.entries.push({ ...this.form });
            }
            this.showForm = false;
            await Alpine.store('app').saveSection('faq', this.entries);
        },

        async removeEntry(index) {
            this.entries.splice(index, 1);
            await Alpine.store('app').saveSection('faq', this.entries);
        },

        async generateAll() {
            const result = await Alpine.store('app').generateText('faq');
            if (result && Array.isArray(result)) {
                this.entries = result;
                await Alpine.store('app').saveSection('faq', this.entries);
            }
        },
    };
}

function stepDesign() {
    return {
        form: {},
        templates: [],

        init() {
            const design = Alpine.store('app').project?.design || {};
            this.templates = Alpine.store('app').templates;
            this.form = {
                template: design.template || 'tropical-fresh',
                color_primary: design.color_primary || '#2E7D5E',
                color_accent: design.color_accent || '#F4A261',
                color_background: design.color_background || '#FAFAF8',
                color_text: design.color_text || '#1A1A1A',
                font_heading: design.font_heading || 'Playfair Display',
                font_body: design.font_body || 'Inter',
                show_map: design.show_map !== false,
                show_prices: design.show_prices !== false,
                show_reviews: design.show_reviews !== false,
                show_faq: design.show_faq !== false,
                footer_text: design.footer_text || '',
            };
        },

        selectTemplate(id) {
            this.form.template = id;
            // Apply template defaults
            const defaults = {
                'tropical-fresh': { color_primary: '#2E7D5E', color_accent: '#F4A261', font_heading: 'Playfair Display', font_body: 'Inter' },
                'modern-minimal': { color_primary: '#1A1A1A', color_accent: '#E63946', font_heading: 'Montserrat', font_body: 'Inter' },
                'warm-rustic': { color_primary: '#8B5E3C', color_accent: '#D4A574', font_heading: 'Lora', font_body: 'Nunito' },
                'luxury-dark': { color_primary: '#C9A96E', color_accent: '#C9A96E', font_heading: 'Raleway', font_body: 'Lato' },
            };
            const d = defaults[id];
            if (d) Object.assign(this.form, d);
        },

        async save() {
            await Alpine.store('app').saveSection('design', this.form);
        },
    };
}

function stepLegal() {
    return {
        form: {},

        init() {
            const legal = Alpine.store('app').project?.legal || {};
            const info = Alpine.store('app').project?.property_info || {};
            this.form = {
                owner_legal_name: legal.owner_legal_name || '',
                owner_address: legal.owner_address || '',
                registration_number: legal.registration_number || '',
                vat_number: legal.vat_number || '',
                responsible_person: legal.responsible_person || info.owner_name || '',
                privacy_policy: legal.privacy_policy || '',
                terms: legal.terms || '',
                acknowledged: legal.acknowledged || false,
            };
        },

        async save() {
            await Alpine.store('app').saveSection('legal', this.form);
        },

        async generatePrivacy() {
            await this.save();
            const text = await Alpine.store('app').generateText('privacy');
            if (text) {
                this.form.privacy_policy = text;
                await this.save();
            }
        },
    };
}

function stepPreview() {
    return {
        previewUrl: '',

        init() {
            const store = Alpine.store('app');
            // Add auth header via a workaround: we fetch and inject
            this.previewUrl = api.previewUrl(store.projectId)
                + '?_t=' + Date.now(); // cache bust
        },

        async refreshPreview() {
            this.previewUrl = api.previewUrl(Alpine.store('app').projectId)
                + '?_t=' + Date.now();
        },

        downloadZip() {
            const store = Alpine.store('app');
            // Open export URL in new tab (browser will download)
            const url = api.exportUrl(store.projectId);
            // We need auth, so fetch as blob
            fetch(url, { headers: { 'Authorization': `Bearer ${AUTH_TOKEN}` } })
                .then(res => res.blob())
                .then(blob => {
                    const a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = `${store.project?.slug || 'website'}-website.zip`;
                    a.click();
                });
        },
    };
}
