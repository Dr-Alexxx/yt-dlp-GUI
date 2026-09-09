<script setup>
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import { store } from '../store'

const runtime = computed(() => store.runtimeStatus)
</script>

<template>
  <div v-if="runtime" style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px">
    <n-tag :type="runtime.ffmpeg.ready ? 'success' : 'warning'" size="small">
      FFmpeg：{{ runtime.ffmpeg.ready ? '已就绪' : '未就绪' }}
    </n-tag>
    <n-tag :type="runtime.cookie.configured ? 'success' : 'default'" size="small">
      Cookie：{{ runtime.cookie.configured ? `已配置（${runtime.cookie.source === 'file' ? runtime.cookie.format : '浏览器'}）` : '未配置' }}
    </n-tag>
    <n-tag type="info" size="small">yt-dlp：{{ runtime.yt_dlp_version }}</n-tag>
  </div>
</template>
