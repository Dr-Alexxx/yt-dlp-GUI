<script setup>
import { computed, h, ref } from 'vue'
import { NButton, NDataTable, NModal, NRadio, NRadioGroup, useMessage } from 'naive-ui'
import { call } from '../api'
import { store } from '../store'
import { switchView } from '../store'

const message = useMessage()

const choice = ref('best')
const visible = computed(() => !!store.probeResult)
const rows = computed(() => store.probeResult?.info?.formats || [])

const QUALITY_NAMES = {
  '30016': '360P', '30032': '480P', '30064': '720P', '30080': '1080P',
  '30112': '1080P 高码率', '30120': '4K', '30125': 'HDR 真彩',
  '30126': '杜比视界', '30127': '8K 超高清',
  '30216': '音频 64K', '30232': '音频 132K', '30280': '音频 192K',
  '30250': '杜比全景声', '30251': 'Hi-Res 无损',
}

const columns = [
  { title: '质量', key: 'quality', width: 130,
    render: (r) => QUALITY_NAMES[r.format_id] || `未知 (${r.format_id})` },
  { title: 'ID', key: 'format_id', width: 90 },
  { title: '容器', key: 'ext', width: 70 },
  { title: '分辨率', key: 'resolution' },
  { title: '大小', key: 'filesize',
    render: (r) => (r.filesize ? (r.filesize / 1048576).toFixed(1) + 'MB' : '-') },
]

const rowProps = (row) => ({
  style: 'cursor: pointer',
  onClick: () => (choice.value = row.format_id),
})

async function start() {
  const format = choice.value === 'best' ? undefined : choice.value
  const options = {}
  if (format) options.format = format
  if (store.audioOnly) options.audio_only = true
  await call('add_task', store.probeResult.url, options)
  store.probeResult = null
}

async function play() {
  const r = await call('start_play', store.probeResult.url, {})
  store.probeResult = null
  if (!r.ok) {
    message.error(r.error)
    return
  }
  store.playerSession = { id: r.session_id, status: 'progress', progress: 0 }
  switchView('player')
}

function dismiss() {
  store.probeResult = null
}
</script>

<template>
  <n-modal
    :show="visible" preset="card" :title="store.probeResult?.info?.title || '选择格式'"
    style="width: 640px" @mask-click="dismiss" @close="dismiss"
  >
    <n-radio-group v-model:value="choice" style="margin-bottom: 8px">
      <n-radio value="best">最佳画质（默认）</n-radio>
      <n-radio v-if="choice !== 'best'" :value="choice">已选：{{ choice }}</n-radio>
    </n-radio-group>
    <n-data-table :columns="columns" :data="rows" size="small" :row-props="rowProps" :max-height="360" />
    <template #footer>
      <n-button type="primary" @click="start">开始下载</n-button>
      <n-button style="margin-left: 8px" @click="play">▶ 在线播放</n-button>
    </template>
  </n-modal>
</template>
