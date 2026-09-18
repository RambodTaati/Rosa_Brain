<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

type Skill = {
  id: string
  name: string
  description?: string
  body?: string
  enabled?: boolean
  ready?: boolean
}

const skills = ref<Skill[]>([])
const error = ref('')
const name = ref('')
const description = ref('')
const body = ref('')
const busy = ref(false)

async function refresh() {
  const res = await api.listSkills()
  skills.value = (res.skills || []) as Skill[]
}

async function addSkill() {
  busy.value = true
  error.value = ''
  try {
    await api.createSkill({ name: name.value, description: description.value, body: body.value, enabled: true })
    name.value = ''
    description.value = ''
    body.value = ''
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

async function prepare(id: string) {
  error.value = ''
  try {
    await api.prepareSkill(id)
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function remove(id: string) {
  if (!confirm('این مهارت حذف شود؟')) return
  await api.deleteSkill(id)
  await refresh()
}

onMounted(async () => {
  try { await refresh() } catch (e) { error.value = e instanceof Error ? e.message : String(e) }
})
</script>

<template>
  <div class="stack">
    <div class="card">
      <h1 style="margin-top:0">مهارت‌ها (Skills)</h1>
      <p class="muted">مهارت جدید معرفی کن تا برای استفاده آماده شود.</p>
      <div class="stack">
        <input v-model="name" placeholder="نام مهارت" />
        <input v-model="description" placeholder="توضیح کوتاه" />
        <textarea v-model="body" placeholder="متن مهارت / دستورالعمل استفاده" />
        <div class="row">
          <button :disabled="busy || !name.trim() || !body.trim()" @click="addSkill">افزودن مهارت</button>
        </div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <div class="card">
      <div v-if="!skills.length" class="muted">هنوز مهارتی ثبت نشده.</div>
      <div v-for="s in skills" :key="s.id" class="list-item">
        <div>
          <strong>{{ s.name }}</strong>
          <div class="muted">{{ s.description || '—' }}</div>
          <div class="row" style="margin-top:0.35rem">
            <span class="badge" :class="s.ready ? 'ok' : 'off'">{{ s.ready ? 'آماده' : 'ناآماده' }}</span>
            <span class="badge" :class="s.enabled ? 'ok' : 'off'">{{ s.enabled ? 'فعال' : 'غیرفعال' }}</span>
          </div>
        </div>
        <div class="row">
          <button class="secondary" @click="prepare(s.id)">آماده‌سازی</button>
          <button class="danger" @click="remove(s.id)">حذف</button>
        </div>
      </div>
    </div>
  </div>
</template>
