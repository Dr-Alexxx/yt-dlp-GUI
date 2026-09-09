<script setup>
import { h, ref } from 'vue'
import {
  NButton, NInput, NProgress, NSwitch, NTag, NDataTable, NCollapse, NCollapseItem, NModal, useMessage,
} from 'naive-ui'
import { call } from '../api'
import { store } from '../store'

const message = useMessage()
const url = ref('')
const batchMode = ref(false)
const batchText = ref('')
const activeError = ref(null)

function showError(row) {
  activeError.value = row
}

async function invoke(row, method) {
  const r = await call(method, row.id)
  if (!r.ok) message.error(r.error)
}

async function copyPath(row) {
  const r = await call('get_task_filepath', row.id)
  if (!r.ok) {
    message.error(r.error)
    return
  }
  try {
    await navigator.clipboard.writeText(r.path)
    message.success('路径已复制')
  } catch {
    message.error('复制失败，请使用“打开目录”定位文件')
  }
}

function openSettings() {
  activeError.value = null
  store.view = 'settings'
}

async function retryFromError() {
  const row = activeError.value
  activeError.value = null
  if (row) await invoke(row, 'retry_task')
}

const statusMap = {
  queued: '排队中', probing: '解析中', waiting: '等待选择',
  downloading: '下载中', done: '完成', error: '失败', cancelled: '已取消',
}

function tagType(s) {
  return { done: 'success', error: 'error', downloading: 'info', waiting: 'warning' }[s] || 'default'
}

function actions(row) {
  const btns = []
  const add = (label, method, onClick = () => call(method, row.id)) => btns.push(
    h(NButton, { size: 'tiny', style: 'margin-right: 6px',
                  onClick }, { default: () => label }))
  if (row.status === 'done') {
    add('打开文件', 'open_task_file', () => invoke(row, 'open_task_file'))
    add('打开目录', 'open_task_directory', () => invoke(row, 'open_task_directory'))
    btns.push(h(NButton, { size: 'tiny', onClick: () => copyPath(row) }, { default: () => '复制路径' }))
    return btns
  }
  if (row.status === 'downloading' || row.status === 'waiting') add('暂停', 'pause_task')
  if (row.status === 'cancelled') add('继续', 'resume_task')
  if (row.status === 'error' || row.status === 'cancelled') add('重试', 'retry_task')
  if (!['done', 'cancelled', 'error'].includes(row.status)) add('取消', 'cancel_task')
  if (row.status === 'error') btns.push(h(NButton, { size: 'tiny', onClick: () => showError(row) }, { default: () => '查看原因' }))
  return btns
}

const columns = [
  { title: '标题', key: 'title', ellipsis: { tooltip: true },
    render: (row) => row.title || row.url },
  { title: '状态', key: 'status', width: 90,
    render: (row) => h(NTag, { size: 'small', type: tagType(row.status) },
      { default: () => statusMap[row.status] }) },
  { title: '进度', key: 'percent', width: 170,
    render: (row) => h(NProgress, { type: 'line', percentage: row.percent,
      indicatorPlacement: 'inside',
      status: row.status === 'error' ? 'error' : 'default' }) },
  { title: '速度', key: 'speed', width: 100 },
  { title: '剩余', key: 'eta', width: 70 },
  { title: '操作', key: 'actions', width: 210, render: actions },
]

async function add() {
  const options = {}
  if (store.audioOnly) options.audio_only = true
  if (store.wantSubtitles) {
    options.subtitles = true
    if (store.subtitleLangs.trim()) options.subtitle_langs = store.subtitleLangs.trim()
  }
  if (store.customUa && store.uaString.trim()) {
    options.custom_ua = true
    options.ua_string = store.uaString.trim()
  }
  if (batchMode.value) {
    const r = await call('add_batch', batchText.value, options)
    if (r.errors?.length) message.error(r.errors.join('；'))
    batchText.value = ''
  } else {
    const r = await call('add_task', url.value, options)
    if (!r.ok) message.error(r.error)
    else url.value = ''
  }
}

async function probe() {
  const target = batchMode.value ? batchText.value.split(/\r?\n/)[0] : url.value
  const ua = store.customUa && store.uaString.trim() ? store.uaString.trim() : null
  const r = await call('probe_url', (target || '').trim(), ua)
  if (!r.ok) {
    message.error(r.error)
    return
  }
  store.probeResult = { url: (target || '').trim(), info: r.info }
}
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 6px; align-items: center; flex-wrap: wrap">
      <span>批量</span>
      <n-switch v-model:value="batchMode" size="small" />
      <span>仅音频 (MP3)</span>
      <n-switch v-model:value="store.audioOnly" size="small" />
      <span>字幕</span>
      <n-switch v-model:value="store.wantSubtitles" size="small" />
    </div>
    <n-collapse style="margin-bottom: 8px">
      <n-collapse-item title="更多下载选项" name="advanced-download-options">
        <n-input
          v-if="store.wantSubtitles" v-model:value="store.subtitleLangs"
          size="small" style="margin-bottom: 8px"
          placeholder="字幕语言，如 zh-CN,en；留空=默认字幕" />
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
          <span>自定义 UA</span>
          <n-switch v-model:value="store.customUa" size="small" />
          <n-input
            v-if="store.customUa" v-model:value="store.uaString" size="small"
            style="min-width: 320px; flex: 1"
            placeholder="粘贴目标网站的 User-Agent（网站页面 F12 控制台输入 navigator.userAgent 回车）" />
        </div>
      </n-collapse-item>
    </n-collapse>
    <n-input
      v-if="!batchMode" v-model:value="url" type="text"
      placeholder="粘贴视频链接" @keyup.enter="add" />
    <n-input
      v-else v-model:value="batchText" type="textarea" :rows="4"
      placeholder="每行一个链接" />
    <n-button type="primary" style="margin: 8px 0 16px" @click="add">
      {{ batchMode ? '批量添加' : '添加下载' }}
    </n-button>
    <n-button style="margin: 8px 0 16px" @click="probe">解析格式…</n-button>
    <n-data-table :columns="columns" :data="store.tasks" size="small" />
    <n-modal
      :show="!!activeError" preset="card" title="下载失败"
      style="width: 620px" @close="activeError = null" @mask-click="activeError = null"
    >
      <div style="white-space: pre-wrap; word-break: break-word">{{ activeError?.error }}</div>
      <template #footer>
        <n-button @click="retryFromError">重新下载</n-button>
        <n-button style="margin-left: 8px" @click="openSettings">打开设置</n-button>
        <n-button style="margin-left: 8px" @click="activeError = null">关闭</n-button>
      </template>
    </n-modal>
  </div>
</template>
