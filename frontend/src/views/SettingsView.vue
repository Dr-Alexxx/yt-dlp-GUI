<script setup>
import { onMounted, ref } from 'vue'
import { NButton, NCollapse, NCollapseItem, NForm, NFormItem, NInput, NInputNumber, NSelect, useMessage } from 'naive-ui'
import { call } from '../api'

const message = useMessage()
const form = ref({
  download_dir: '', cookie_file: '', cookie_file_format: 'netscape',
  cookies_browser: '', subtitle_langs: '', max_concurrent: 2,
})

const browserOptions = [
  { label: '不使用浏览器 Cookie', value: '' },
  { label: 'Chrome', value: 'chrome' },
  { label: 'Edge', value: 'edge' },
  { label: 'Firefox', value: 'firefox' },
]

const formatOptions = [
  { label: 'Netscape 格式 (cookies.txt)', value: 'netscape' },
  { label: 'JSON 格式', value: 'json' },
]

async function browseCookie() {
  try {
    const r = await call('pick_cookie_file')
    if (r.ok && r.path) form.value.cookie_file = r.path
    else if (!r.ok) message.error(r.error)
  } catch (e) {
    message.error('打开文件对话框失败：' + e)
  }
}

async function browseDir() {
  try {
    const r = await call('pick_download_dir')
    if (r.ok && r.path) form.value.download_dir = r.path
    else if (!r.ok) message.error(r.error)
  } catch (e) {
    message.error('打开文件夹对话框失败：' + e)
  }
}

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
      <n-button style="margin-left: 8px" @click="browseDir">浏览…</n-button>
    </n-form-item>
    <n-form-item label="Cookie 文件路径">
      <n-input v-model:value="form.cookie_file" placeholder="可选，cookies.txt 或 .json 路径" />
      <n-button style="margin-left: 8px" @click="browseCookie">浏览…</n-button>
    </n-form-item>
    <n-form-item label="Cookie 文件格式">
      <n-select v-model:value="form.cookie_file_format" :options="formatOptions" />
    </n-form-item>
    <n-collapse style="margin: 0 0 12px 150px; max-width: 560px">
      <n-collapse-item title="如何导入 Cookie？（B 站 1080P 等登录画质需要）" name="cookie-help">
        <div style="font-size: 13px; line-height: 1.8">
          <p style="margin: 0 0 6px">三种方法任选其一，得到 <b>cookies.txt</b> 后把完整路径填到上方「Cookie 文件路径」，保存即可（「浏览器 Cookie」保持「不使用」）：</p>
          <p style="margin: 0 0 6px"><b>格式选择</b>：扩展/工具导出的 cookies.txt 选 <b>Netscape 格式</b>；导出的是 .json（如 EditThisCookie）则选 <b>JSON 格式</b>（对象数组或简单键值对均可）。</p>
          <p style="margin: 0 0 6px"><b>方法一：浏览器扩展（推荐）</b><br />
            Edge/Chrome 安装扩展 <i>Get cookies.txt LOCALLY</i> → 登录 bilibili.com → 在 B 站页面点扩展图标 → Export 保存。</p>
          <p style="margin: 0 0 6px"><b>方法二：GetCookie 工具</b><br />
            下载 github.com/ytdl-patched/GetCookie 的 Release exe，双击自动生成 cookies.txt。</p>
          <p style="margin: 0 0 6px"><b>方法三：yt-dlp 命令行</b><br />
            关闭浏览器后运行：yt-dlp --cookies-from-browser edge --cookies cookies.txt --skip-download "https://www.bilibili.com"</p>
          <p style="margin: 4px 0 0; color: #e8a33d">⚠ cookies.txt 是你的登录凭证，不要分享给任何人；画质变化后可重新导出。</p>
        </div>
      </n-collapse-item>
    </n-collapse>
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
