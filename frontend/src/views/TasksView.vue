<script setup>
import { h, ref } from 'vue'
import {
  NButton, NInput, NProgress, NSwitch, NTag, NDataTable, useMessage,
} from 'naive-ui'
import { call } from '../api'
import { store } from '../store'

const message = useMessage()
const url = ref('')
const batchMode = ref(false)
const batchText = ref('')

const statusMap = {
  queued: '排队中', probing: '解析中', waiting: '等待选择',
  downloading: '下载中', done: '完成', error: '失败', cancelled: '已取消',
}

function tagType(s) {
  return { done: 'success', error: 'error', downloading: 'info', waiting: 'warning' }[s] || 'default'
}

function actions(row) {
  const btns = []
  const add = (label, method) => btns.push(
    h(NButton, { size: 'tiny', style: 'margin-right: 6px',
                 onClick: () => call(method, row.id) }, { default: () => label }))
  if (row.status === 'downloading' || row.status === 'waiting') add('暂停', 'pause_task')
  if (row.status === 'cancelled') add('继续', 'resume_task')
  if (row.status === 'error' || row.status === 'cancelled') add('重试', 'retry_task')
  if (!['done', 'cancelled', 'error'].includes(row.status)) add('取消', 'cancel_task')
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
  const r = await call('probe_url', (target || '').trim())
  if (!r.ok) {
    message.error(r.error)
    return
  }
  store.probeResult = { url: (target || '').trim(), info: r.info }
}
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 6px; align-items: center">
      <span>批量</span>
      <n-switch v-model:value="batchMode" size="small" />
      <span>仅音频 (MP3)</span>
      <n-switch v-model:value="store.audioOnly" size="small" />
      <span>字幕</span>
      <n-switch v-model:value="store.wantSubtitles" size="small" />
      <n-input
        v-if="store.wantSubtitles" v-model:value="store.subtitleLangs"
        size="small" style="width: 220px"
        placeholder="语言，如 zh-CN,en；留空=默认字幕" />
    </div>
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
  </div>
</template>
