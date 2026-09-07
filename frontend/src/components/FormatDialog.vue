<script setup>
import { computed, ref } from 'vue'
import { NButton, NModal, NRadio, NRadioGroup, useMessage } from 'naive-ui'
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

function sizeMB(r) {
  return r.filesize ? (r.filesize / 1048576).toFixed(0) + 'MB' : '未知'
}

function codecLabel(vcodec) {
  const v = (vcodec || '').toLowerCase()
  if (!v || v === 'none') return ''
  if (v.startsWith('avc') || v.startsWith('h264')) return 'AVC (H.264)'
  if (v.startsWith('hvc') || v.startsWith('hev')) return 'HEVC (H.265)'
  if (v.startsWith('av01') || v.startsWith('av1')) return 'AV1'
  return ''
}

// 为每个条目附加：清晰度层级 / 编码标签 / 是否音频 / 是否推荐 / 大小
const annotated = computed(() => rows.value.map((r) => {
  const isAudio = (r.vcodec || '') === 'none' || /audio only/i.test(r.resolution || '')
  let tier = ''
  if (isAudio) {
    tier = QUALITY_NAMES[r.format_id] || '音频'
  } else {
    const m = (r.resolution || '').match(/(\d+)x(\d+)/)
    const height = m ? Number(m[2]) : 0
    for (const [id, name] of Object.entries(QUALITY_NAMES)) {
      if (id === r.format_id) { tier = name; break }
    }
    if (!tier) tier = height ? `${height}P` : (r.resolution || r.format_id)
  }
  const codec = codecLabel(r.vcodec)
  return { ...r, isAudio, tier, codec, size: sizeMB(r) }
}))

// 同一清晰度下多个相同编码 → 大的标"高码率"
const groups = computed(() => {
  const out = []
  const map = new Map()
  for (const item of annotated.value) {
    if (!map.has(item.tier)) { map.set(item.tier, []); out.push(map.get(item.tier)) }
    map.get(item.tier).push(item)
  }
  // 组内标记：同 tier 同 codec 有多个时，体积最大的为高码率；推荐 AVC
  for (const g of out) {
    const byCodec = new Map()
    for (const it of g) byCodec.set(it.codec || '_', (byCodec.get(it.codec || '_') || []).concat(it))
    for (const list of byCodec.values()) {
      if (list.length > 1) list.sort((a, b) => (b.filesize || 0) - (a.filesize || 0))
      const maxId = list[0] && list.length > 1 ? list[0].format_id : null
      if (list.length > 1 && maxId) list[0].highBitrate = true
    }
    g.forEach((it) => { it.recommended = !it.isAudio && (it.codec || '').includes('AVC') && !it.highBitrate })
  }
  // 排序：非音频按清晰度降序（音频置后），组内推荐项在前
  const tierRank = new Map()
  annotated.value.forEach((it, i) => { if (!tierRank.has(it.tier)) tierRank.set(it.tier, i) })
  out.forEach((g) => g.sort((a, b) => (b.recommended ? 1 : 0) - (a.recommended ? 1 : 0)))
  out.sort((a, b) => {
    const aA = a[0].isAudio ? 1 : 0
    const bA = b[0].isAudio ? 1 : 0
    if (aA !== bA) return aA - bA
    return (tierRank.get(a[0].tier) || 0) - (tierRank.get(b[0].tier) || 0)
  })
  return out
})

function pickItem(it) {
  choice.value = it.format_id
}

function labelOf(it) {
  const extras = [it.codec, it.highBitrate ? '高码率' : '', it.recommended ? '推荐' : ''].filter(Boolean)
  return extras.length ? extras.join(' · ') : it.format_id
}

async function start() {
  const format = choice.value === 'best' ? undefined : choice.value
  const options = {}
  if (format) options.format = format
  if (store.audioOnly) options.audio_only = true
  await call('add_task', store.probeResult.url, options)
  store.probeResult = null
}

async function play() {
  const options = {}
  if (store.customUa && store.uaString.trim()) {
    options.custom_ua = true
    options.ua_string = store.uaString.trim()
  }
  const r = await call('start_play', store.probeResult.url, options)
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
      <n-radio value="best">最佳画质（默认，自动选最高且兼容）</n-radio>
    </n-radio-group>

    <div style="max-height: 360px; overflow: auto">
      <div v-for="g in groups" :key="g[0].tier" style="margin-bottom: 8px">
        <div style="font-weight: 600; margin: 4px 0">{{ g[0].tier }}</div>
        <div
          v-for="it in g" :key="it.format_id"
          @click="pickItem(it)"
          :style="{
            padding: '4px 8px', cursor: 'pointer', borderRadius: '4px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            background: choice === it.format_id ? 'rgba(63,72,255,0.18)' : 'transparent',
          }"
        >
          <span>
            {{ labelOf(it) }} <span style="color: #888">({{ it.size }})</span>
          </span>
          <span style="color: #888; font-size: 12px">ID {{ it.format_id }}</span>
        </div>
      </div>
      <div v-if="!groups.length" style="color: #888; padding: 12px">该视频没有可选的清晰度</div>
    </div>

    <template #footer>
      <n-button type="primary" @click="start">开始下载</n-button>
      <n-button style="margin-left: 8px" @click="play">▶ 在线播放</n-button>
    </template>
  </n-modal>
</template>
