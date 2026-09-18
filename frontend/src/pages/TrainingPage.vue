<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api'

type Dict = Record<string, unknown>

const data = ref<Dict | null>(null)
const resources = ref<Dict | null>(null)
const error = ref('')
const refreshing = ref(false)
const corpusTab = ref('skills_postgres')
const classifyText = ref('سلام')
const classifyResult = ref<Dict | null>(null)
const classifyBusy = ref(false)
const classifyError = ref('')
let timer: number | undefined

function num(v: unknown, d = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? n : d
}

function pct(v: unknown) {
  const n = num(v, NaN)
  if (!Number.isFinite(n)) return '—'
  const x = n <= 1 && n >= 0 ? n * 100 : n
  return `${x.toFixed(1)}%`
}

function fmtLoss(v: unknown) {
  const n = num(v, NaN)
  if (!Number.isFinite(n)) return '—'
  return n.toFixed(4)
}

function fmtBytes(v: unknown) {
  const n = num(v, 0)
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function fmtAge(v: unknown) {
  const n = num(v, NaN)
  if (!Number.isFinite(n)) return '—'
  if (n < 60) return `${Math.round(n)} ثانیه پیش`
  if (n < 3600) return `${Math.round(n / 60)} دقیقه پیش`
  return `${(n / 3600).toFixed(1)} ساعت پیش`
}

function fmtTime(ts: unknown) {
  const n = num(ts, NaN)
  if (!Number.isFinite(n)) return '—'
  try {
    return new Date(n * 1000).toLocaleString('fa-IR', { hour12: false })
  } catch {
    return String(ts)
  }
}

const progress = computed(() => (data.value?.progress as Dict) || {})
const metrics = computed(() => (data.value?.metrics as Dict) || {})
const method = computed(() => (data.value?.method as Dict) || {})
const roadmap = computed(() => (data.value?.roadmap as Dict[]) || [])
const rounds = computed(() => (data.value?.completed_rounds_detail as Dict[]) || [])
const history = computed(() => ([...(data.value?.recent_history as Dict[] || [])]).reverse())
const trend = computed(() => (data.value?.trend as Dict[]) || [])
const corpus = computed(() => (data.value?.corpus as Record<string, Dict[]>) || {})
const corpusCounts = computed(() => (data.value?.corpus_counts as Record<string, number>) || {})

const corpusTabs = computed(() => {
  const preferred = [
    'skills_postgres',
    'skills_security_defensive',
    'skills_windows',
    'skills_ubuntu',
    'skills_fullstack_agent',
    'skills_quiz',
    'understand_en',
    'understand_fa',
    'english',
    'persian',
    'other',
  ]
  const labels: Record<string, string> = {
    skills_postgres: 'PostgreSQL',
    skills_security_defensive: 'امنیت دفاعی',
    skills_windows: 'Windows',
    skills_ubuntu: 'Ubuntu',
    skills_fullstack_agent: 'Full-stack',
    skills_quiz: 'Quiz',
    understand_en: 'Understand EN',
    understand_fa: 'Understand FA',
    english: 'English',
    persian: 'Persian',
    other: 'سایر',
  }
  return preferred
    .filter((k) => (corpusCounts.value[k] || 0) > 0 || (corpus.value[k] || []).length > 0)
    .map((k) => ({ id: k, label: labels[k] || k, count: corpusCounts.value[k] || (corpus.value[k] || []).length }))
})

const focusFiles = computed(() => (data.value?.current_focus_files as string[]) || [])

const statusTone = computed(() => {
  if (!data.value) return 'off'
  if (data.value.phase === 'done') return 'ok'
  if (data.value.learner_likely_running) return 'ok'
  return 'warn'
})

const statusLabel = computed(() => {
  if (!data.value) return 'نامشخص'
  if (data.value.phase === 'done') return 'مسیر فعلی تمام شده'
  if (data.value.learner_likely_running) return 'در حال آموزش'
  return 'متوقف / در انتظار'
})

const chartPoints = computed(() => {
  const pts = trend.value
  if (!pts.length) return ''
  const w = 320
  const h = 72
  const vals = pts.map((p) => num(p.pct, 0))
  const max = Math.max(100, ...vals)
  const min = Math.min(0, ...vals)
  const span = Math.max(1, max - min)
  return vals
    .map((v, i) => {
      const x = (i / Math.max(1, vals.length - 1)) * w
      const y = h - ((v - min) / span) * (h - 8) - 4
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

async function load() {
  refreshing.value = true
  try {
    const [learn, res] = await Promise.all([api.learning(), api.resources().catch(() => null)])
    data.value = learn
    if (res) resources.value = res
    error.value = ''
    if (corpusTabs.value.length && !corpusTabs.value.some((t) => t.id === corpusTab.value)) {
      corpusTab.value = corpusTabs.value[0].id
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    refreshing.value = false
  }
}

async function runClassify() {
  classifyBusy.value = true
  classifyError.value = ''
  classifyResult.value = null
  try {
    classifyResult.value = await api.classify(classifyText.value.trim())
  } catch (e) {
    classifyError.value = e instanceof Error ? e.message : String(e)
  } finally {
    classifyBusy.value = false
  }
}

onMounted(async () => {
  await load()
  timer = window.setInterval(load, 4000)
})
onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="stack training-page" dir="rtl">
    <div class="card">
      <div class="row" style="justify-content: space-between; align-items: flex-start">
        <div>
          <h1 style="margin: 0 0 0.35rem">آموزش و پیشرفت</h1>
          <p class="muted" style="margin: 0">داشبورد زندهٔ Rosa_Brain — هر ۴ ثانیه تازه می‌شود.</p>
        </div>
        <div class="row">
          <span class="badge" :class="statusTone">{{ statusLabel }}</span>
          <button class="secondary" type="button" :disabled="refreshing" @click="load">
            {{ refreshing ? 'در حال تازه کردن…' : 'تازه‌سازی' }}
          </button>
        </div>
      </div>
      <div class="row" style="margin-top: 0.85rem">
        <span class="badge">mode: {{ data?.mode || '—' }}</span>
        <span class="badge">{{ data?.round_label || data?.phase || '—' }}</span>
        <span class="badge" :class="data?.checkpoint_exists ? 'ok' : 'off'">
          checkpoint {{ data?.checkpoint_exists ? 'OK' : 'missing' }}
        </span>
        <span class="badge">دستگاه: {{ data?.device || resources?.recommended_device || '—' }}</span>
        <span class="badge">آخرین رویداد: {{ fmtAge(data?.last_event_age_seconds) }}</span>
      </div>
      <p v-if="error" class="error" style="margin-top: 0.75rem">{{ error }}</p>
    </div>

    <div class="grid-2" v-if="data">
      <div class="card">
        <div class="row" style="justify-content: space-between">
          <strong>پیشرفت کلی</strong>
          <span class="metric-val">{{ num(progress.overall_percent).toFixed(1) }}%</span>
        </div>
        <div class="progress lg" style="margin-top: 0.55rem">
          <span :style="{ width: Math.min(100, num(progress.overall_percent)) + '%' }" />
        </div>
        <div class="row" style="margin-top: 1rem; justify-content: space-between">
          <strong>راند فعلی</strong>
          <span class="metric-val">{{ num(progress.round_percent).toFixed(1) }}%</span>
        </div>
        <div class="progress lg" style="margin-top: 0.55rem">
          <span :style="{ width: Math.min(100, num(progress.round_percent)) + '%' }" />
        </div>
        <p class="muted" style="margin: 0.85rem 0 0">
          راند {{ data.round_id || 0 }} از {{ data.total_rounds || '—' }}
          · تمام‌شده: {{ data.completed_rounds || 0 }}
          · skill: {{ data.skill || '—' }}
        </p>
      </div>

      <div class="card">
        <h3 style="margin-top: 0">متریک‌های زنده</h3>
        <div class="metrics">
          <div class="metric">
            <span class="muted">Loss</span>
            <strong>{{ fmtLoss(metrics.loss ?? data.recent_avg_loss) }}</strong>
            <span class="muted tiny">هدف {{ fmtLoss(metrics.loss_target ?? data.round_target_loss) }}</span>
          </div>
          <div class="metric">
            <span class="muted">Held-out</span>
            <strong>{{ pct(metrics.heldout_pct ?? data.heldout_accuracy) }}</strong>
            <span class="muted tiny">هدف {{ pct(metrics.acc_target_pct ?? data.acc_target) }}</span>
          </div>
          <div class="metric">
            <span class="muted">Detect / Quiz</span>
            <strong>{{ pct(metrics.detect_pct ?? data.detect_accuracy) }} / {{ pct(metrics.quiz_pct ?? data.quiz_accuracy) }}</strong>
          </div>
          <div class="metric">
            <span class="muted">Steps</span>
            <strong>{{ data.phase_steps || 0 }} / {{ data.round_min_steps || '—' }}</strong>
            <span class="muted tiny">کل {{ data.total_steps || '—' }}</span>
          </div>
        </div>
        <p class="muted" style="margin: 0.75rem 0 0">
          سیاست امنیت: {{ data.security_policy === 'defensive_only_no_exploits' ? 'فقط دفاعی (بدون اکسپلویت)' : data.security_policy }}
        </p>
      </div>
    </div>

    <div class="grid-2" v-if="data">
      <div class="card">
        <h3 style="margin-top: 0">نقشهٔ مسیر</h3>
        <ul class="roadmap">
          <li v-for="r in roadmap" :key="String(r.id)" :class="{ done: !!r.done }">
            <span class="dot" />
            <span>{{ r.label }}</span>
            <span class="badge" :class="r.done ? 'ok' : 'off'">{{ r.done ? 'انجام شد' : 'باقی‌مانده' }}</span>
          </li>
        </ul>
        <div v-if="rounds.length" style="margin-top: 1rem">
          <h4 style="margin: 0 0 0.5rem">راندهای تمام‌شده</h4>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>برچسب</th>
                  <th>Loss</th>
                  <th>Acc</th>
                  <th>Steps</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in rounds" :key="String(r.round_id) + String(r.label)">
                  <td>{{ r.round_id }}</td>
                  <td>{{ r.label }}</td>
                  <td>{{ fmtLoss(r.loss) }}</td>
                  <td>{{ pct(r.acc) }}</td>
                  <td>{{ r.steps }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="row" style="justify-content: space-between">
          <h3 style="margin: 0">روند پیشرفت</h3>
          <span class="muted mono">{{ data.trend_sparkline || '—' }}</span>
        </div>
        <svg v-if="chartPoints" class="trend-chart" viewBox="0 0 320 72" role="img" aria-label="نمودار روند">
          <polyline fill="none" stroke="currentColor" stroke-width="2.5" :points="chartPoints" />
        </svg>
        <p v-else class="muted">هنوز دادهٔ روند نیست.</p>
        <h4 style="margin: 0.75rem 0 0.5rem">تاریخچهٔ اخیر</h4>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>زمان</th>
                <th>فاز</th>
                <th>%</th>
                <th>Loss</th>
                <th>Held-out</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(h, i) in history.slice(0, 12)" :key="i">
                <td>{{ fmtTime(h.ts) }}</td>
                <td>{{ h.round_label || h.phase }}</td>
                <td>{{ num(h.combined_percent).toFixed(1) }}</td>
                <td>{{ fmtLoss(h.recent_avg_loss) }}</td>
                <td>{{ pct(h.heldout_accuracy ?? h.detect_accuracy) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="grid-2" v-if="data">
      <div class="card">
        <h3 style="margin-top: 0">منابع سیستم</h3>
        <div class="metrics" v-if="resources">
          <div class="metric">
            <span class="muted">GPU</span>
            <strong>{{ resources.gpu_name || '—' }}</strong>
            <span class="muted tiny">
              VRAM {{ num(resources.gpu_vram_allocated_gb).toFixed(2) }} /
              {{ num(resources.gpu_vram_total_gb).toFixed(1) }} GB
            </span>
          </div>
          <div class="metric">
            <span class="muted">CPU</span>
            <strong>{{ num(resources.cpu_percent).toFixed(1) }}%</strong>
            <span class="muted tiny">{{ resources.cpu_count }} هسته</span>
          </div>
          <div class="metric">
            <span class="muted">RAM</span>
            <strong>{{ num(resources.ram_percent).toFixed(1) }}%</strong>
            <span class="muted tiny">
              آزاد {{ num(resources.ram_available_gb).toFixed(1) }} /
              {{ num(resources.ram_total_gb).toFixed(1) }} GB
            </span>
          </div>
          <div class="metric">
            <span class="muted">آموزش</span>
            <strong>{{ resources.can_train ? 'آماده' : 'غیرفعال' }}</strong>
            <span class="muted tiny">batch {{ resources.suggested_batch_size }} · seq {{ resources.suggested_seq_len }}</span>
          </div>
        </div>
        <p v-else class="muted">منابع در دسترس نیست.</p>
        <p class="muted tiny" style="margin-top: 0.75rem">
          checkpoint: <code>{{ data.checkpoint }}</code>
        </p>
      </div>

      <div class="card">
        <h3 style="margin-top: 0">تست تشخیص معنی</h3>
        <p class="muted" style="margin-top: 0">یک جمله بفرست تا `/v1/classify` را زنده ببینی.</p>
        <div class="row">
          <input class="grow" v-model="classifyText" @keydown.enter.prevent="runClassify" placeholder="مثلاً سلام" />
          <button type="button" :disabled="classifyBusy || !classifyText.trim()" @click="runClassify">
            {{ classifyBusy ? '…' : 'تشخیص' }}
          </button>
        </div>
        <p v-if="classifyError" class="error">{{ classifyError }}</p>
        <div v-if="classifyResult" class="msg bot" style="margin-top: 0.75rem">
          <div><strong>{{ (classifyResult as any).label || (classifyResult as any).meaning || '—' }}</strong></div>
          <div class="muted">confidence: {{ pct((classifyResult as any).confidence ?? (classifyResult as any).score) }}</div>
          <pre class="json-block">{{ JSON.stringify(classifyResult, null, 2) }}</pre>
        </div>
      </div>
    </div>

    <div class="card" v-if="data">
      <h3 style="margin-top: 0">کورپوس و فایل‌های تمرکز</h3>
      <div class="row tabs">
        <button
          v-for="t in corpusTabs"
          :key="t.id"
          type="button"
          class="secondary"
          :class="{ active: corpusTab === t.id }"
          @click="corpusTab = t.id"
        >
          {{ t.label }} ({{ t.count }})
        </button>
      </div>
      <div class="table-wrap" style="margin-top: 0.75rem">
        <table>
          <thead>
            <tr>
              <th>فایل</th>
              <th>حجم</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in (corpus[corpusTab] || [])" :key="String(f.file)">
              <td><code>{{ f.file }}</code></td>
              <td>{{ fmtBytes(f.bytes) }}</td>
            </tr>
            <tr v-if="!(corpus[corpusTab] || []).length">
              <td colspan="2" class="muted">فایلی در این گروه نیست.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="focusFiles.length" style="margin-top: 1rem">
        <h4 style="margin: 0 0 0.5rem">تمرکز فعلی</h4>
        <ul class="focus-list">
          <li v-for="f in focusFiles" :key="f"><code>{{ f }}</code></li>
        </ul>
      </div>
    </div>

    <div class="card" v-if="data">
      <h3 style="margin-top: 0">روش و محدودیت‌ها</h3>
      <p style="margin-top: 0">
        موتور: {{ method.engine || 'TinyBrainNet' }}
        · بدون مدل ازپیش‌آموزش‌دیده: {{ method.no_pretrained ? 'بله' : 'خیر' }}
      </p>
      <ol class="order-list">
        <li v-for="(step, i) in ((method.order as string[]) || [])" :key="i">{{ step }}</li>
      </ol>
    </div>

    <div v-if="!data && !error" class="card">
      <p class="muted">در حال بارگذاری داشبورد آموزش…</p>
    </div>
  </div>
</template>
