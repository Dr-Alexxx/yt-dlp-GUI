<script setup>
import { computed, ref } from 'vue'
import { NButton, NCheckbox, NCheckboxGroup, NModal, NScrollbar } from 'naive-ui'
import { call } from '../api'
import { store } from '../store'

const checked = ref([])
const visible = computed(() => !!store.pendingPlaylist)

function dismiss() {
  store.pendingPlaylist = null
  checked.value = []
}

async function submit() {
  await call('submit_playlist_selection', store.pendingPlaylist.task_id, checked.value)
  dismiss()
}
</script>

<template>
  <n-modal
    :show="visible" preset="card" title="选择要下载的播放列表条目"
    style="width: 560px" @mask-click="dismiss" @close="dismiss"
  >
    <n-checkbox-group v-model:value="checked">
      <n-scrollbar style="max-height: 400px">
        <div v-for="e in store.pendingPlaylist?.entries || []" :key="e.index" style="padding: 2px 0">
          <n-checkbox :value="e.index" :label="`${e.index}. ${e.title}`" />
        </div>
      </n-scrollbar>
    </n-checkbox-group>
    <template #footer>
      <n-button type="primary" :disabled="!checked.length" @click="submit">
        下载选中项（{{ checked.length }}）
      </n-button>
    </template>
  </n-modal>
</template>
