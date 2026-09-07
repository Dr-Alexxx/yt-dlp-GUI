<script setup>
import { computed } from 'vue'
import { NButton, NProgress } from 'naive-ui'
import { call } from '../api'
import { store } from '../store'

const s = computed(() => store.playerSession)

async function close() {
  await call('stop_play', s.value.id)
  store.playerSession = null
  store.view = 'tasks'
}
</script>

<template>
  <div v-if="s">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
      <b>在线播放</b>
      <n-button size="small" @click="close">关闭并删除</n-button>
    </div>
    <div v-if="s.status === 'progress'" style="max-width: 560px">
      <p>正在临时下载（{{ s.progress }}%）…</p>
      <n-progress type="line" :percentage="s.progress" />
      <p style="color: #999; font-size: 12px">
        下载完成后自动开始播放；临时文件在关闭播放或退出应用时删除
      </p>
    </div>
    <div v-else-if="s.status === 'ready'">
      <video
        :src="`http://127.0.0.1:${s.port}/${encodeURIComponent(s.filename)}`"
        controls autoplay
        style="width: 100%; max-height: 70vh; background: #000"
      />
    </div>
    <div v-else>
      <p>播放失败：{{ s.error }}</p>
      <n-button @click="close">返回</n-button>
    </div>
  </div>
</template>
