<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'

type Server = {
  id: string
  name: string
  description?: string
  transport?: string
  command?: string
  args?: string[]
  url?: string
  enabled?: boolean
  ready?: boolean
}

const servers = ref<Server[]>([])
const error = ref('')
const name = ref('')
const description = ref('')
const transport = ref('stdio')
const command = ref('')
const argsText = ref('')
const url = ref('')
const busy = ref(false)

async function refresh() {
  const res = await api.listMcp()
  servers.value = (res.servers || []) as Server[]
}

async function addServer() {
  busy.value = true
  error.value = ''
  try {
    const args = argsText.value.split(',').map((x) => x.trim()).filter(Boolean)
    await api.createMcp({
      name: name.value,
      description: description.value,
      transport: transport.value,
      command: command.value,
      args,
      url: url.value,
      enabled: false,
    })
    name.value = ''
    description.value = ''
    command.value = ''
    argsText.value = ''
    url.value = ''
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
    await api.prepareMcp(id)
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function remove(id: string) {
  if (!confirm('این MCP حذف شود؟')) return
  await api.deleteMcp(id)
  await refresh()
}

onMounted(async () => {
  try { await refresh() } catch (e) { error.value = e instanceof Error ? e.message : String(e) }
})
</script>

<template>
  <div class="stack">
    <div class="card">
      <h1 style="margin-top:0">MCPها</h1>
      <p class="muted">سرور MCP را معرفی کن تا Rosa_Brain بتواند از ابزارهایش استفاده کند. توکن/رمز را اینجا ذخیره نکن.</p>
      <div class="stack">
        <input v-model="name" placeholder="نام MCP" />
        <input v-model="description" placeholder="توضیح" />
        <select v-model="transport" aria-label="نوع اتصال">
          <option value="stdio">stdio</option>
          <option value="sse">sse</option>
          <option value="http">http</option>
        </select>
        <input v-if="transport === 'stdio'" v-model="command" placeholder="فرمان اجرا (مثلاً npx)" />
        <input v-if="transport === 'stdio'" v-model="argsText" placeholder="آرگومان‌ها با ویرگول" />
        <input v-if="transport !== 'stdio'" v-model="url" placeholder="URL سرور MCP" />
        <button :disabled="busy || !name.trim()" @click="addServer">افزودن MCP</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <div class="card">
      <div v-if="!servers.length" class="muted">هنوز MCPی ثبت نشده.</div>
      <div v-for="s in servers" :key="s.id" class="list-item">
        <div>
          <strong>{{ s.name }}</strong>
          <div class="muted">{{ s.description || '—' }} · {{ s.transport }}</div>
          <div class="muted" v-if="s.command"><code>{{ s.command }} {{ (s.args || []).join(' ') }}</code></div>
          <div class="muted" v-if="s.url"><code>{{ s.url }}</code></div>
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
