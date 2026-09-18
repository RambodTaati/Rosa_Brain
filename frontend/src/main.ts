import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './styles.css'

const app = createApp(App)
app.config.errorHandler = (err) => {
  console.error('Rosa_Brain UI error', err)
}
app.use(router)
app.mount('#app')
