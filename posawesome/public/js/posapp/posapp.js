import Home from './Home.vue';

frappe.provide('frappe.PosApp');

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
