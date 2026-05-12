<script setup>
import { computed, onMounted, ref } from 'vue'
import { createExport, deleteJob, exportDownloadUrl, getJob, imagePreviewUrl, listJobs, saveItems, uploadImages } from './api/client'

const view = ref('upload')
const jobs = ref([])
const currentJob = ref(null)
const selectedFiles = ref([])
const busy = ref(false)
const error = ref('')
const accessToken = ref(localStorage.getItem('accessToken') || '')

const totalAmount = computed(() => calculateJobTotal('amount'))
const totalTax = computed(() => calculateJobTotal('tax'))

onMounted(loadJobs)

function setAccessToken() {
  localStorage.setItem('accessToken', accessToken.value.trim())
}

async function loadJobs() {
  try {
    jobs.value = await listJobs()
  } catch (err) {
    error.value = err.message
  }
}

async function submitUpload() {
  if (!selectedFiles.value.length) {
    error.value = '请选择图片'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const job = await uploadImages(selectedFiles.value)
    currentJob.value = normalizeJob(job)
    view.value = 'detail'
    selectedFiles.value = []
    await loadJobs()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function openJob(jobId) {
  busy.value = true
  error.value = ''
  try {
    currentJob.value = normalizeJob(await getJob(jobId))
    view.value = 'detail'
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function saveCurrentJob() {
  if (!currentJob.value) return
  busy.value = true
  error.value = ''
  try {
    currentJob.value = normalizeJob(await saveItems(currentJob.value.id, currentJob.value.groups))
    await loadJobs()
    return true
  } catch (err) {
    error.value = err.message
    throw err
  } finally {
    busy.value = false
  }
}

async function exportCurrentJob() {
  if (!currentJob.value) return
  busy.value = true
  error.value = ''
  try {
    await saveItems(currentJob.value.id, currentJob.value.groups)
    const file = await createExport(currentJob.value.id)
    window.location.href = exportDownloadUrl(file.id)
    await loadJobs()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function removeJob(jobId) {
  busy.value = true
  error.value = ''
  try {
    await deleteJob(jobId)
    if (currentJob.value?.id === jobId) currentJob.value = null
    await loadJobs()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

function onFileChange(event) {
  selectedFiles.value = Array.from(event.target.files || [])
}

function addItem(group) {
  group.items.push({
    id: null,
    group_id: group.id,
    image_file_id: null,
    raw_text: '',
    amount: 0,
    tax: 0,
    bbox_x: null,
    bbox_y: null,
    bbox_w: null,
    bbox_h: null,
    ocr_confidence: null,
    is_manual: true,
    is_corrected: true,
  })
}

function removeItem(group, index) {
  group.items.splice(index, 1)
  recalculateGroup(group)
}

function markCorrected(item, group) {
  item.is_corrected = true
  recalculateGroup(group)
}

function recalculateGroup(group) {
  group.amount_total = round2(group.items.reduce((sum, item) => sum + numberValue(item.amount), 0))
  group.tax_total = round2(group.items.reduce((sum, item) => sum + numberValue(item.tax), 0))
  group.formula_amount = formula(group.items.map((item) => item.amount))
  group.formula_tax = formula(group.items.map((item) => item.tax))
}

function calculateJobTotal(field) {
  if (!currentJob.value) return '0.00'
  const key = field === 'amount' ? 'amount_total' : 'tax_total'
  return round2(currentJob.value.groups.reduce((sum, group) => sum + numberValue(group[key]), 0)).toFixed(2)
}

function normalizeJob(job) {
  for (const group of job.groups || []) {
    recalculateGroup(group)
  }
  return job
}

function numberValue(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function round2(value) {
  return Math.round((numberValue(value) + Number.EPSILON) * 100) / 100
}

function formula(values) {
  const usable = values.map(numberValue).filter((value) => value !== 0)
  return usable.length ? usable.map((value) => round2(value).toFixed(2)).join(' + ') : '0.00'
}

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleString()
}
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <h1>Invoice OCR</h1>
        <p>按颜色框分组识别金额与税费</p>
      </div>
      <nav>
        <button :class="{ active: view === 'upload' }" @click="view = 'upload'">上传</button>
        <button :class="{ active: view === 'history' }" @click="view = 'history'; loadJobs()">历史</button>
      </nav>
    </header>

    <section class="token-row">
      <label>访问口令</label>
      <input v-model="accessToken" type="password" placeholder="如服务端配置 ACCESS_TOKEN 则填写" @change="setAccessToken" />
      <button @click="setAccessToken">保存</button>
    </section>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="busy" class="status">处理中...</p>

    <section v-if="view === 'upload'" class="panel upload-panel">
      <h2>上传图片</h2>
      <input type="file" multiple accept=".png,.jpg,.jpeg,image/png,image/jpeg" @change="onFileChange" />
      <div class="selected-files">
        <span v-for="file in selectedFiles" :key="file.name">{{ file.name }}</span>
      </div>
      <button class="primary" :disabled="busy" @click="submitUpload">开始识别</button>
    </section>

    <section v-if="view === 'history'" class="panel">
      <h2>历史记录</h2>
      <table class="jobs-table">
        <thead>
          <tr>
            <th>文件</th>
            <th>状态</th>
            <th>含税金额</th>
            <th>税费</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id">
            <td>{{ job.original_filenames.join(', ') }}</td>
            <td>{{ job.status }}</td>
            <td>{{ job.amount_total.toFixed(2) }}</td>
            <td>{{ job.tax_total.toFixed(2) }}</td>
            <td>{{ formatDate(job.created_at) }}</td>
            <td class="actions">
              <button @click="openJob(job.id)">打开</button>
              <button class="danger" @click="removeJob(job.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="view === 'detail' && currentJob" class="detail-layout">
      <aside class="panel summary-panel">
        <h2>识别结果</h2>
        <div class="metric">
          <span>含税金额</span>
          <strong>{{ totalAmount }}</strong>
        </div>
        <div class="metric">
          <span>税费</span>
          <strong>{{ totalTax }}</strong>
        </div>
        <div class="file-list">
          <figure v-for="image in currentJob.images" :key="image.id" class="preview">
            <img :src="imagePreviewUrl(image.id)" :alt="image.original_name" />
            <figcaption>{{ image.original_name }}</figcaption>
          </figure>
        </div>
        <button class="primary" :disabled="busy" @click="saveCurrentJob">保存修改</button>
        <button :disabled="busy" @click="exportCurrentJob">导出 Excel</button>
      </aside>

      <section class="groups">
        <article v-for="group in currentJob.groups" :key="group.id" class="group-panel">
          <header class="group-header">
            <div class="group-title">
              <span class="swatch" :style="{ backgroundColor: group.color_hex }"></span>
              <h3>{{ group.display_name }}</h3>
            </div>
            <button @click="addItem(group)">新增明细</button>
          </header>
          <div class="group-totals">
            <span>含税金额：{{ group.amount_total.toFixed(2) }}</span>
            <span>税费：{{ group.tax_total.toFixed(2) }}</span>
          </div>
          <div class="formula">
            <p>金额：{{ group.formula_amount }}</p>
            <p>税费：{{ group.formula_tax }}</p>
          </div>
          <table class="items-table">
            <thead>
              <tr>
                <th>识别文本</th>
                <th>含税金额</th>
                <th>税费</th>
                <th>来源</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in group.items" :key="item.id || index">
                <td>
                  <textarea v-model="item.raw_text" @input="markCorrected(item, group)"></textarea>
                </td>
                <td>
                  <input v-model.number="item.amount" type="number" step="0.01" @input="markCorrected(item, group)" />
                </td>
                <td>
                  <input v-model.number="item.tax" type="number" step="0.01" @input="markCorrected(item, group)" />
                </td>
                <td>
                  <span v-if="item.is_manual">人工新增</span>
                  <span v-else>OCR</span>
                </td>
                <td>
                  <button class="danger" @click="removeItem(group, index)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </article>
      </section>
    </section>
  </main>
</template>
