<template>
  <v-app class="container1">
    <v-main>
      <Navbar @changePage="setPage($event)"></Navbar>
      <component v-bind:is="page" class="mx-4 md-4"></component>
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

<style scoped>
.container1 {
  margin-top: 0px;
}
</style>

<style>
html.posawesome-shell-active .navbar,
html.posawesome-shell-active .page-head,
html.posawesome-shell-active .layout-side-section,
html.posawesome-shell-active .standard-sidebar {
  display: none !important;
}

html.posawesome-shell-active .page-container,
html.posawesome-shell-active .layout-main-section-wrapper,
html.posawesome-shell-active .layout-main-section {
  margin-top: 0 !important;
  padding-top: 0 !important;
}
</style>
