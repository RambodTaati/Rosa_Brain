<script setup lang="ts">
import { onMounted, ref, nextTick, computed } from 'vue'
import { api } from '../api'

type Msg = { role: 'user' | 'bot'; text: string }
type Project = { id: string; name: string; description?: string }

const messages = ref<Msg[]>([])
const input = ref('')
const busy = ref(false)
const deleting = ref(false)
const error = ref('')
const projects = ref<Project[]>([])
const projectId = ref('')
const newProjectName = ref('')
const sessionId = ref(`s-${Date.now()}`)
const box = ref<HTMLElement | null>(null)

const selectedProject = computed(() => projects.value.find((p) => p.id === projectId.value) || null)

async function refreshProjects() {
  const res = await api.listProjects()
  projects.value = (res.projects || []) as Project[]
  if (projectId.value && !projects.value.some((p) => p.id === projectId.value)) {
    projectId.value = ''
  }
}

async function createProject() {
  const name = newProjectName.value.trim()
  if (!name) return
  error.value = ''
  try {
    const p = await api.createProject(name)
    newProjectName.value = ''
    await refreshProjects()
    projectId.value = String(p.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function deleteSelectedProject() {
  const p = selectedProject.value
  if (!p || deleting.value) return
  const ok = window.confirm(`پروژه «${p.name}» حذف شود؟ این کار برگشت‌پذیر نیست.`)
  if (!ok) return
  deleting.value = true
  error.value = ''
  try {
    await api.deleteProject(p.id)
    if (projectId.value === p.id) projectId.value = ''
    await refreshProjects()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    deleting.value = false
  }
}

async function send() {
  const text = input.value.trim()
  if (!text || busy.value) return
  busy.value = true
  error.value = ''
  messages.value.push({ role: 'user', text })
  input.value = ''
  await nextTick()
  box.value?.scrollTo({ top: box.value.scrollHeight })
  try {
    const res = await api.chat(text, sessionId.value, projectId.value || undefined)
    const reply = String(res.reply || res.message || res.text || JSON.stringify(res))
    messages.value.push({ role: 'bot', text: reply })
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    messages.value.push({ role: 'bot', text: 'خطا در پاسخ. لطفاً دوباره پیام بفرستید.' })
  } finally {
    busy.value = false
    await nextTick()
    box.value?.scrollTo({ top: box.value.scrollHeight })
  }
}

onMounted(async () => {
  try {
    await refreshProjects()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})
</script>

<template>
  <div class="stack" dir="rtl">
    <div class="card">
      <h1 style="margin:0 0 0.5rem">گفتگو با Rosa_Brain</h1>
      <p class="muted" style="margin:0">اینجا می‌توانید چت کنید و روی یک پروژه فعال کار کنید.</p>
      <div class="row" style="margin-top:1rem">
        <select v-model="projectId" class="grow" aria-label="پروژه فعال">
          <option value="">بدون پروژه</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <input
          v-model="newProjectName"
          class="grow"
          placeholder="نام پروژه جدید"
          @keyup.enter="createProject"
        />
        <button class="secondary" type="button" :disabled="!newProjectName.trim()" @click="createProject">
          ساخت پروژه
        </button>
        <button
          class="danger"
          type="button"
          :disabled="!selectedProject || deleting"
          :title="selectedProject ? `حذف «${selectedProject.name}»` : 'ابتدا یک پروژه را انتخاب کنید'"
          @click="deleteSelectedProject"
        >
          {{ deleting ? 'در حال حذف…' : 'حذف پروژه' }}
        </button>
      </div>
      <p v-if="selectedProject" class="muted" style="margin:0.65rem 0 0">
        پروژه انتخاب‌شده: <strong>{{ selectedProject.name }}</strong>
        <span v-if="selectedProject.description"> — {{ selectedProject.description }}</span>
      </p>
    </div>

    <div class="card" ref="box" style="min-height:360px; max-height:55vh; overflow:auto">
      <div v-if="!messages.length" class="muted">هنوز پیامی نیست. یک سؤال یا دستور بنویسید.</div>
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role" style="margin-bottom:0.6rem">{{ m.text }}</div>
    </div>

    <div class="card">
      <div class="row">
        <input
          v-model="input"
          class="grow"
          placeholder="پیام خود را بنویسید…"
          :disabled="busy"
          @keyup.enter="send"
        />
        <button type="button" :disabled="busy || !input.trim()" @click="send">{{ busy ? '…' : 'ارسال' }}</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>
