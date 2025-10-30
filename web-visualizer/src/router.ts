import { createRouter, createWebHashHistory } from 'vue-router';
import Home from './views/Home.vue';
import Map from './views/Map.vue';

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: Home },
    { path: '/map', name: 'map', component: Map }
  ]
});

export default router;



