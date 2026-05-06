import Home from './Home.vue';

frappe.provide('frappe.PosApp');

function registerPosAppServiceWorker() {
    if (typeof window === 'undefined' || typeof navigator === 'undefined') return;
    if (!('serviceWorker' in navigator)) return;
    if (!window.location || !/^\/app\/posapp\/?$/.test(window.location.pathname || '')) return;

    const collectAssetUrls = () => {
        const urls = new Set([window.location.href]);
        const selectors = [
            'script[src]',
            'link[rel="stylesheet"][href]',
            'link[rel="preload"][href]',
            'img[src]',
        ];
        selectors.forEach((selector) => {
            document.querySelectorAll(selector).forEach((el) => {
                const raw = el.getAttribute('src') || el.getAttribute('href') || '';
                if (!raw) return;
                try {
                    const url = new URL(raw, window.location.origin);
                    if (url.origin === window.location.origin) urls.add(url.href);
                } catch (e) {}
            });
        });
        try {
            performance.getEntriesByType('resource').forEach((entry) => {
                const raw = entry && entry.name;
                if (!raw) return;
                const url = new URL(raw, window.location.origin);
                if (
                    url.origin === window.location.origin &&
                    (
                        url.pathname.startsWith('/assets/') ||
                        url.pathname.startsWith('/files/') ||
                        url.pathname === '/app/posapp'
                    )
                ) {
                    urls.add(url.href);
                }
            });
        } catch (e) {}
        return Array.from(urls);
    };

    const currentBundle = (() => {
        try {
            const scripts = Array.from(document.querySelectorAll('script[src]'));
            const found = scripts
                .map((script) => script.getAttribute('src') || '')
                .find((src) => /posawesome\.bundle\./.test(src) || /posawesome\.bundle\.js/.test(src));
            return found || 'posawesome-bundle';
        } catch (e) {
            return 'posawesome-bundle';
        }
    })();

    const swUrl = `/posawesome-posapp-sw.js?v=${encodeURIComponent(currentBundle)}`;
    navigator.serviceWorker
        .register(swUrl, { scope: '/app/posapp' })
        .then((registration) => {
            const sendPrecache = () => {
                const worker = registration.active || registration.waiting || registration.installing;
                if (!worker) return;
                worker.postMessage({
                    type: 'POSAPP_PRECACHE_URLS',
                    urls: collectAssetUrls(),
                });
            };
            sendPrecache();
            if (registration.installing) {
                registration.installing.addEventListener('statechange', sendPrecache);
            }
            setTimeout(sendPrecache, 3000);
        })
        .catch(() => {});
}

registerPosAppServiceWorker();

frappe.PosApp.posapp = class {
    constructor(ctx) {
        this.$doc = $(document);
        // Frappe page contexts are inconsistent across versions/custom shells.
        // Accept either `{ parent: {...} }`, `{ page: {...} }`, or the page object itself.
        const root = (ctx && ctx.parent) ? ctx.parent : ctx;
        this.page = (root && root.page) ? root.page : root;
        this.make_body();
    }

    resolve_mount_el() {
        const pageMain = this.page && this.page.main ? $(this.page.main) : $();
        if (pageMain && pageMain.length) return pageMain.first();

        const fallbackSelectors = [
            '.page-container .main-section',
            '.layout-main-section .main-section',
            '.layout-main-section-wrapper .main-section',
            '.main-section',
        ];

        for (const selector of fallbackSelectors) {
            const $el = this.$doc.find(selector);
            if ($el && $el.length) return $el.first();
        }

        return $();
    }

    make_body () {
        this.$el = this.resolve_mount_el();
        if (!this.$el || !this.$el.length || !this.$el[0]) {
            // Leave a clear runtime signal instead of crashing on local shells.
            // Cypress/runtime capture hooks read this and fail fast with context.
            console.error(new Error('POSAwesome mount target not found (.main-section)'));
            return;
        }
        this.vue = new Vue({
            vuetify: new Vuetify(
                {
                    rtl: frappe.utils.is_rtl(),
                    theme: {
                        themes: {
                            light: {
                                background: '#FFFFFF',
                                primary: '#0097A7',
                                secondary: '#00BCD4',
                                accent: '#9575CD',
                                success: '#66BB6A',
                                info: '#2196F3',
                                warning: '#FF9800',
                                error: '#E86674',
                                orange: '#E65100',
                                golden: '#A68C59',
                                badge: '#F5528C',
                                customPrimary: '#085294',
                            },
                        },
                    },
                }
            ),
            el: this.$el[0],
            data: {
            },
            render: h => h(Home),
        });
    }
    setup_header () {

    }

};
