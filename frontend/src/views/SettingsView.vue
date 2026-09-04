<script setup>
import { onMounted, ref } from 'vue'
import { NButton, NForm, NFormItem, NInput, NInputNumber, NSelect, useMessage } from 'naive-ui'
import { call } from '../api'

const message = useMessage()
const form = ref({
  download_dir: '', cookie_file: '', cookies_browser: '',
  subtitle_langs: '', max_concurrent: 2,
})

const browserOptions = [
  { label: '不使用浏览器 Cookie', value: '' },
  { label: 'Chrome', value: 'chrome' },
  { label: 'Edge', value: 'edge' },
  { label: 'Firefox', value: 'firefox' },
]

onMounted(async () => {
  const r = await call('get_config')
  if (r.ok) Object.assign(form.value, r.config)
})

async function save() {
  await call('save_config', { ...form.value, max_concurrent: Number(form.value.max_concurrent) })
  message.success('已保存')
}
</script>

<template>
  <n-form label-placement="left" label-width="150" style="max-width: 560px">
    <n-form-item label="下载目录">
      <n-input v-model:value="form.download_dir" />
    </n-form-item>
    <n-form-item label="Cookie 文件路径">
      <n-input v-model:value="form.cookie_file" placeholder="可选，cookies.txt 路径" />
    </n-form-item>
    <n-form-item label="浏览器 Cookie">
      <n-select v-model:value="form.cookies_browser" :options="browserOptions" />
    </n-form-item>
    <n-form-item label="字幕语言">
      <n-input v-model:value="form.subtitle_langs" placeholder="逗号分隔，如 zh-CN,en；留空不下字幕" />
    </n-form-item>
    <n-form-item label="并发下载数">
      <n-input-number v-model:value="form.max_concurrent" :min="1" :max="5" />
    </n-form-item>
    <n-button type="primary" @click="save">保存</n-button>
  </n-form>
</template>
