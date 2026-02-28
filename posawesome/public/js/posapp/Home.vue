<template>
  <v-app class="posawesome-shell-app">
    <v-main class="posawesome-shell-main">
      <Navbar @changePage="setPage($event)"></Navbar>
      <component v-bind:is="page" class="posawesome-page-shell"></component>
    </v-main>
  </v-app>
</template>

<script>
import Navbar from './components/Navbar.vue';
import POS from './components/pos/Pos.vue';
import Payments from './components/payments/Pay.vue';

export default {
  data: function () {
    return {
      page: 'POS',
    };
  },
  components: {
    Navbar,
    POS,
    Payments,
  },
  methods: {
    setPage(page) {
      this.page = page;
    },
    setShellChromeActive(isActive) {
      const cls = 'posawesome-shell-active';
      const roots = [document.documentElement, document.body].filter(Boolean);
      roots.forEach((el) => {
        if (isActive) {
          el.classList.add(cls);
        } else {
          el.classList.remove(cls);
        }
      });
    },
  },
  mounted() {
    this.setShellChromeActive(true);
  },
  beforeDestroy() {
    this.setShellChromeActive(false);
  },
};
</script>

<style>
html.posawesome-shell-active .navbar,
html.posawesome-shell-active .page-head,
html.posawesome-shell-active .layout-side-section,
html.posawesome-shell-active .standard-sidebar {
  display: none !important;
}

html.posawesome-shell-active .page-container,
html.posawesome-shell-active .layout-main-section-wrapper,
html.posawesome-shell-active .layout-main-section,
html.posawesome-shell-active .main-section {
  margin-top: 0 !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
  padding-top: 0 !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}

html.posawesome-shell-active,
html.posawesome-shell-active body,
html.posawesome-shell-active #body,
html.posawesome-shell-active .page-container,
html.posawesome-shell-active .layout-main-section-wrapper,
html.posawesome-shell-active .layout-main-section,
html.posawesome-shell-active .main-section {
  background: #f4f7fb !important;
}

html.posawesome-shell-active .page-container,
html.posawesome-shell-active .layout-main-section-wrapper,
html.posawesome-shell-active .layout-main-section,
html.posawesome-shell-active .main-section,
html.posawesome-shell-active .v-application,
html.posawesome-shell-active .v-application--wrap,
html.posawesome-shell-active .v-main {
  min-height: 100vh;
}

html.posawesome-shell-active .posawesome-shell-app,
html.posawesome-shell-active .posawesome-shell-main,
html.posawesome-shell-active .posawesome-page-shell {
  min-height: 100vh;
  background: #f4f7fb !important;
}
</style>
