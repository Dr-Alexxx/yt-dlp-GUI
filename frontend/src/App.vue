<script setup>
import { onMounted } from 'vue'
import {
  NConfigProvider, NLayout, NLayoutSider, NLayoutContent,
  NMenu, NMessageProvider, darkTheme, zhCN, dateZhCN,
} from 'naive-ui'
import TasksView from './views/TasksView.vue'
import SettingsView from './views/SettingsView.vue'
import FfmpegBanner from './components/FfmpegBanner.vue'
import PlaylistDialog from './components/PlaylistDialog.vue'
import FormatDialog from './components/FormatDialog.vue'
import { store, initStore } from './store'

onMounted(initStore)
</script>

<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-message-provider>
      <n-layout style="height: 100vh" has-sider>
        <n-layout-sider :width="150">
          <n-menu
            :value="store.view"
            :options="[{ label: '下载', key: 'tasks' }, { label: '设置', key: 'settings' }]"
            @update:value="(v) => (store.view = v)"
          />
        </n-layout-sider>
        <n-layout-content content-style="padding: 16px">
          <FfmpegBanner />
          <TasksView v-if="store.view === 'tasks'" />
          <SettingsView v-else />
        </n-layout-content>
      </n-layout>
      <PlaylistDialog />
      <FormatDialog />
    </n-message-provider>
  </n-config-provider>
</template>
