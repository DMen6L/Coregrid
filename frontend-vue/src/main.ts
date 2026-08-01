import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import { VueQueryPlugin, QueryClient } from "@tanstack/vue-query";
import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import "./styles/main.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

createApp(App)
  .use(router)
  .use(VueQueryPlugin, { queryClient })
  .mount("#app");
