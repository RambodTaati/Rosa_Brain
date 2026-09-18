import { createRouter, createWebHistory } from 'vue-router'
import ChatPage from './pages/ChatPage.vue'
import TrainingPage from './pages/TrainingPage.vue'
import SkillsPage from './pages/SkillsPage.vue'
import McpPage from './pages/McpPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'chat', component: ChatPage },
    { path: '/training', name: 'training', component: TrainingPage },
    { path: '/skills', name: 'skills', component: SkillsPage },
    { path: '/mcp', name: 'mcp', component: McpPage },
  ],
})
