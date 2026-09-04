<script setup>
import { NAlert, NButton, NProgress } from 'naive-ui'
import { call } from '../api'
import { store } from '../store'
</script>

<template>
  <n-alert
    v-if="!store.ffmpegPath && store.ffmpegProgress === null && !store.ffmpegError"
    type="warning" style="margin-bottom: 12px"
  >
    FFmpeg 未就绪，音频提取 / 格式合并功能不可用
    <n-button size="tiny" style="margin-left: 8px" @click="call('download_ffmpeg')">
      自动下载到应用目录
    </n-button>
  </n-alert>
  <n-alert v-else-if="store.ffmpegProgress !== null" type="info" style="margin-bottom: 12px">
    正在下载 FFmpeg…
    <n-progress type="line" :percentage="store.ffmpegProgress" />
  </n-alert>
  <n-alert v-else-if="store.ffmpegError" type="error" style="margin-bottom: 12px" closable @close="store.ffmpegError = ''">
    FFmpeg 下载失败：{{ store.ffmpegError }}
    <n-button size="tiny" style="margin-left: 8px" @click="store.ffmpegError = ''; call('download_ffmpeg')">
      重试
    </n-button>
  </n-alert>
  <n-alert
    v-if="store.audioOnlyHint && !store.ffmpegPath && store.ffmpegProgress === null"
    type="warning" style="margin-bottom: 12px" closable
    @close="store.audioOnlyHint = false"
  >
    检测到刚完成的任务只得到纯音频文件：FFmpeg 未就绪，无法合并视频 + 音频流。
    点击上方「自动下载到应用目录」后重新下载即可得到完整视频。
  </n-alert>
</template>
