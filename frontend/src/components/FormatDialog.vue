<script setup>
import { computed, h, ref } from 'vue'
import { NButton, NDataTable, NModal, NRadio, NRadioGroup } from 'naive-ui'
import { call } from '../api'
import { store } from '../store'

const choice = ref('best')
const visible = computed(() => !!store.probeResult)
const rows = computed(() => store.probeResult?.info?.formats || [])

const columns = [
  { title: 'ID', key: 'format_id', width: 100 },
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
  await call('add_task', store.probeResult.url, format ? { format } : {})
  store.probeResult = null
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
    </template>
  </n-modal>
</template>
