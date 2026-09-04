import { reactive } from 'vue'
import { call } from './api'

export const store = reactive({
  tasks: [],
  view: 'tasks',
  ffmpegPath: null,
  ffmpegProgress: null,
  ffmpegError: '',
  pendingPlaylist: null,
  probeResult: null,
  audioOnly: false,
  audioOnlyHint: false,
  cookieFallback: false,
})

const AUDIO_EXT_RE = /\.(m4a|mp3|aac|opus|ogg|wav|flac)$/i

export async function initStore() {
  window.__pushEvent = (e) => {
    if (e.type === 'task_update') {
      const i = store.tasks.findIndex((t) => t.id === e.task.id)
      if (i >= 0) store.tasks.splice(i, 1, e.task)
      else store.tasks.unshift(e.task)
      if (e.task.status === 'done' && !store.ffmpegPath &&
          AUDIO_EXT_RE.test(e.task.filepath || '')) {
        store.audioOnlyHint = true
      }
    } else if (e.type === 'need_playlist') {
      store.pendingPlaylist = e
    } else if (e.type === 'cookie_fallback') {
      store.cookieFallback = true
    } else if (e.type === 'ffmpeg_progress') {
      if (e.percent === -1) {
        store.ffmpegProgress = null
        store.ffmpegError = e.error
      } else if (e.percent >= 100) {
        store.ffmpegProgress = null
        call('check_ffmpeg').then((r) => { store.ffmpegPath = r.path })
      } else {
        store.ffmpegProgress = e.percent
      }
    }
  }
  const r = await call('get_task_list')
  if (r.ok) store.tasks = r.tasks
  const f = await call('check_ffmpeg')
  store.ffmpegPath = f.path
}
