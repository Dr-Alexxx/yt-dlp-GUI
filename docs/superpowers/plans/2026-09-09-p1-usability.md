# P1 Usability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce first-time-user confusion by surfacing runtime state, simplifying download options, and adding actionable completed/failed task controls.

**Architecture:** Keep the existing pywebview bridge and Vue state store. Add small JsApi methods for environment and completed-file actions; derive all new UI feedback from existing task state and runtime status rather than changing yt-dlp download semantics.

**Tech Stack:** Python / pywebview / yt-dlp / Vue 3 / Naive UI / pytest.

**Spec:** User-approved P1 scope from the 2026-09-09 project review (bounded enhancement batch; no separate design spec).

## Global Constraints

- Preserve the existing download queue, Cookie, FFmpeg, subtitle, format-selection, playlist, and playback behavior.
- All new Python behavior must be covered by pytest and follow RED-GREEN TDD.
- API methods return `{ok: bool, ...}` and never expose Cookie values.
- Windows-only file actions use `os.startfile`; reject unfinished/missing task files with a Chinese error.
- Frontend must pass `npm run build`; full backend suite must pass before each task is committed.
- P1 does not add new dependencies or real-time streaming.

---

### Task 1: Runtime Status API

**Files:**
- Modify: `backend/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: `JsApi.get_runtime_status() -> dict`:

```python
{
    "ok": True,
    "ffmpeg": {"ready": bool, "path": str | None},
    "cookie": {"configured": bool, "source": "file" | "browser" | "none", "format": str | None},
    "yt_dlp_version": str,
}
```

- Cookie status must never include a file path or cookie contents.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_api.py`:

```python
def test_runtime_status_without_cookie_or_ffmpeg(monkeypatch):
    import backend.api as api_mod
    monkeypatch.setattr(api_mod, "find_ffmpeg", lambda cfg: None)
    api, _ = make_api()
    r = api.get_runtime_status()
    assert r["ok"] is True
    assert r["ffmpeg"] == {"ready": False, "path": None}
    assert r["cookie"] == {"configured": False, "source": "none", "format": None}
    assert isinstance(r["yt_dlp_version"], str) and r["yt_dlp_version"]


def test_runtime_status_reports_cookie_source_without_path(monkeypatch):
    import backend.api as api_mod
    monkeypatch.setattr(api_mod, "find_ffmpeg", lambda cfg: "C:/ffmpeg/ffmpeg.exe")
    api, _ = make_api()
    api.config.data.update({
        "cookie_file": "C:/secret/cookies.txt",
        "cookie_file_format": "json",
        "cookies_browser": "edge",
    })
    r = api.get_runtime_status()
    assert r["ffmpeg"] == {"ready": True, "path": "C:/ffmpeg/ffmpeg.exe"}
    assert r["cookie"] == {"configured": True, "source": "file", "format": "json"}
    assert "secret" not in repr(r)
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
E:\videodown\.venv\Scripts\python -m pytest tests/test_api.py::test_runtime_status_without_cookie_or_ffmpeg tests/test_api.py::test_runtime_status_reports_cookie_source_without_path -v
```

Expected: FAIL with `AttributeError: 'JsApi' object has no attribute 'get_runtime_status'`.

- [ ] **Step 3: Implement minimal API**

In `backend/api.py`, import the yt-dlp version module:

```python
from yt_dlp.version import __version__ as YT_DLP_VERSION
```

Append to `JsApi`:

```python
    def get_runtime_status(self):
        ffmpeg = find_ffmpeg(self.config)
        cookie_file = self.config.get("cookie_file")
        cookies_browser = self.config.get("cookies_browser")
        if cookie_file:
            cookie = {
                "configured": True,
                "source": "file",
                "format": self.config.get("cookie_file_format") or "netscape",
            }
        elif cookies_browser:
            cookie = {"configured": True, "source": "browser", "format": None}
        else:
            cookie = {"configured": False, "source": "none", "format": None}
        return {
            "ok": True,
            "ffmpeg": {"ready": bool(ffmpeg), "path": ffmpeg},
            "cookie": cookie,
            "yt_dlp_version": YT_DLP_VERSION,
        }
```

- [ ] **Step 4: Verify GREEN and full suite**

```powershell
E:\videodown\.venv\Scripts\python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/api.py tests/test_api.py
git commit -m "feat: expose safe runtime status"
```

---

### Task 2: Completed Task File Actions

**Files:**
- Modify: `backend/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces:

```python
open_task_file(task_id) -> {"ok": bool, "error"?: str}
open_task_directory(task_id) -> {"ok": bool, "error"?: str}
get_task_filepath(task_id) -> {"ok": bool, "path"?: str, "error"?: str}
```

- Only `done` tasks with an existing `filepath` are valid.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_api.py`:

```python
def test_completed_task_file_actions(monkeypatch, tmp_path):
    import backend.api as api_mod

    file_path = tmp_path / "video.mp4"
    file_path.write_bytes(b"x")
    api, manager = make_api()
    manager.tasks["done"] = type("Task", (), {"status": "done", "filepath": str(file_path)})()
    manager.tasks["pending"] = type("Task", (), {"status": "downloading", "filepath": str(file_path)})()
    calls = []
    monkeypatch.setattr(api_mod.os, "startfile", lambda path: calls.append(path), raising=False)

    assert api.get_task_filepath("done") == {"ok": True, "path": str(file_path)}
    assert api.open_task_file("done") == {"ok": True}
    assert api.open_task_directory("done") == {"ok": True}
    assert calls == [str(file_path), str(tmp_path)]
    assert api.open_task_file("pending")["ok"] is False
    assert api.open_task_file("missing")["ok"] is False
```

- [ ] **Step 2: Verify RED**

```powershell
E:\videodown\.venv\Scripts\python -m pytest tests/test_api.py::test_completed_task_file_actions -v
```

Expected: FAIL with missing `get_task_filepath` / `open_task_file`.

- [ ] **Step 3: Implement minimal file validation and actions**

Add imports to `backend/api.py`:

```python
import os
from pathlib import Path
```

Append to `JsApi`:

```python
    def _completed_filepath(self, task_id):
        task = self.manager.tasks.get(task_id)
        if task is None:
            return None, "任务不存在"
        status = getattr(task.status, "value", task.status)
        filepath = getattr(task, "filepath", "")
        if status != "done" or not filepath:
            return None, "任务尚未完成"
        path = Path(filepath)
        if not path.is_file():
            return None, "下载文件不存在或已被移动"
        return path, None

    def get_task_filepath(self, task_id):
        path, error = self._completed_filepath(task_id)
        return {"ok": False, "error": error} if error else {"ok": True, "path": str(path)}

    def open_task_file(self, task_id):
        path, error = self._completed_filepath(task_id)
        if error:
            return {"ok": False, "error": error}
        os.startfile(str(path))
        return {"ok": True}

    def open_task_directory(self, task_id):
        path, error = self._completed_filepath(task_id)
        if error:
            return {"ok": False, "error": error}
        os.startfile(str(path.parent))
        return {"ok": True}
```

- [ ] **Step 4: Verify GREEN and full suite**

```powershell
E:\videodown\.venv\Scripts\python -m pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/api.py tests/test_api.py
git commit -m "feat: add completed task file actions"
```

---

### Task 3: Runtime Status Bar and Download Option Layout

**Files:**
- Create: `frontend/src/components/RuntimeStatusBar.vue`
- Modify: `frontend/src/store.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/views/TasksView.vue`

**Interfaces:**
- Consumes: `call('get_runtime_status')` from Task 1.
- Produces: `store.runtimeStatus` with API result; `refreshRuntimeStatus()` export; download options grouped into common toggles and a collapsed advanced area.

- [ ] **Step 1: Add runtime store fields and refresh helper**

In `frontend/src/store.js`, add to `store`:

```js
  runtimeStatus: null,
```

Append:

```js
export async function refreshRuntimeStatus() {
  const r = await call('get_runtime_status')
  if (r.ok) store.runtimeStatus = r
}
```

At the end of `initStore()`, after `check_ffmpeg`, call:

```js
  await refreshRuntimeStatus()
```

In the `ffmpeg_progress` success branch, after `check_ffmpeg`, also call `refreshRuntimeStatus()`.

- [ ] **Step 2: Create `RuntimeStatusBar.vue`**

```vue
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
```

- [ ] **Step 3: Mount the status bar**

In `frontend/src/App.vue` import and render before `FfmpegBanner`:

```js
import RuntimeStatusBar from './components/RuntimeStatusBar.vue'
```

```vue
<RuntimeStatusBar />
<FfmpegBanner />
```

- [ ] **Step 4: Reorganize download options**

In `TasksView.vue`, import `NCollapse` and `NCollapseItem`.

Replace the current option block with:

```vue
    <div style="display: flex; gap: 12px; margin-bottom: 6px; align-items: center; flex-wrap: wrap">
      <span>批量</span>
      <n-switch v-model:value="batchMode" size="small" />
      <span>仅音频 (MP3)</span>
      <n-switch v-model:value="store.audioOnly" size="small" />
      <span>字幕</span>
      <n-switch v-model:value="store.wantSubtitles" size="small" />
    </div>
    <n-collapse style="margin-bottom: 8px">
      <n-collapse-item title="更多下载选项" name="advanced-download-options">
        <n-input
          v-if="store.wantSubtitles" v-model:value="store.subtitleLangs"
          size="small" style="margin-bottom: 8px"
          placeholder="字幕语言，如 zh-CN,en；留空=默认字幕" />
        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
          <span>自定义 UA</span>
          <n-switch v-model:value="store.customUa" size="small" />
          <n-input
            v-if="store.customUa" v-model:value="store.uaString" size="small"
            style="min-width: 320px; flex: 1"
            placeholder="粘贴目标网站的 User-Agent（网站页面 F12 控制台输入 navigator.userAgent 回车）" />
        </div>
      </n-collapse-item>
    </n-collapse>
```

- [ ] **Step 5: Build and verify**

```powershell
cd frontend
npm run build
cd ..
E:\videodown\.venv\Scripts\python -m pytest tests/ -q
```

Expected: frontend build succeeds; all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/components/RuntimeStatusBar.vue frontend/src/store.js frontend/src/App.vue frontend/src/views/TasksView.vue
git commit -m "feat: add runtime status bar and simplify download options"
```

---

### Task 4: Actionable Completed and Failed Task UI

**Files:**
- Modify: `frontend/src/views/TasksView.vue`

**Interfaces:**
- Consumes: `open_task_file`, `open_task_directory`, `get_task_filepath` from Task 2.
- Produces: Done-task actions (open file/open folder/copy path) and an error modal with retry/settings/copy-error actions.

- [ ] **Step 1: Add UI state and imports**

Extend the Naive UI import with `NModal` and add:

```js
const activeError = ref(null)

function showError(row) {
  activeError.value = row
}

async function invoke(row, method) {
  const r = await call(method, row.id)
  if (!r.ok) message.error(r.error)
}

async function copyPath(row) {
  const r = await call('get_task_filepath', row.id)
  if (!r.ok) {
    message.error(r.error)
    return
  }
  try {
    await navigator.clipboard.writeText(r.path)
    message.success('路径已复制')
  } catch {
    message.error('复制失败，请使用“打开目录”定位文件')
  }
}

function openSettings() {
  activeError.value = null
  store.view = 'settings'
}

async function retryFromError() {
  const row = activeError.value
  activeError.value = null
  if (row) await invoke(row, 'retry_task')
}
```

- [ ] **Step 2: Extend task action rendering**

At the start of `actions(row)`, add:

```js
  if (row.status === 'done') {
    add('打开文件', 'open_task_file')
    add('打开目录', 'open_task_directory')
    btns.push(h(NButton, { size: 'tiny', onClick: () => copyPath(row) }, { default: () => '复制路径' }))
    return btns
  }
```

For error tasks, add a visible reason button:

```js
  if (row.status === 'error') btns.push(h(NButton, { size: 'tiny', onClick: () => showError(row) }, { default: () => '查看原因' }))
```

- [ ] **Step 3: Add error modal under the table**

```vue
    <n-modal
      :show="!!activeError" preset="card" title="下载失败"
      style="width: 620px" @close="activeError = null" @mask-click="activeError = null"
    >
      <div style="white-space: pre-wrap; word-break: break-word">{{ activeError?.error }}</div>
      <template #footer>
        <n-button @click="retryFromError">重新下载</n-button>
        <n-button style="margin-left: 8px" @click="openSettings">打开设置</n-button>
        <n-button style="margin-left: 8px" @click="activeError = null">关闭</n-button>
      </template>
    </n-modal>
```

- [ ] **Step 4: Build and verify**

```powershell
cd frontend
npm run build
cd ..
E:\videodown\.venv\Scripts\python -m pytest tests/ -q

Expected: frontend build succeeds; all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/views/TasksView.vue
git commit -m "feat: add completed file actions and actionable error dialog"
```

---

### Task 5: P1 Final Verification and Windows Package

**Files:**
- Modify: `README.md` (update feature bullets only if all P1 features are complete)

- [ ] **Step 1: Run full verification**

```powershell
E:\videodown\.venv\Scripts\python -m pytest tests/ -q
cd frontend
npm run build
cd ..
E:\videodown\.venv\Scripts\python smoke.py
```

Expected: tests pass; frontend builds; smoke exits 0.

- [ ] **Step 2: Rebuild Windows artifact**

```powershell
E:\videodown\.venv\Scripts\pyinstaller app.spec --noconfirm --distpath release --workpath build
```

If Windows reports `PermissionError` for `release\yt-dlp-GUI`, close `yt-dlp-GUI.exe` and rerun the command.

- [ ] **Step 3: Manual GUI checklist**

Run `release\yt-dlp-GUI\yt-dlp-GUI.exe` and verify:

1. Runtime status bar displays FFmpeg, Cookie, and yt-dlp version without exposing Cookie path/value.
2. Common download options stay concise; subtitle language and UA are inside “更多下载选项”.
3. Completed task can open file and directory; copying path shows feedback.
4. Failed task opens the error modal; retry and settings actions work.

- [ ] **Step 4: Update README feature list**

Add these feature bullets under `## 功能` if verification passes:

```markdown
- **运行环境状态**：主页显示 FFmpeg、Cookie 和内置 yt-dlp 版本状态
- **任务快捷操作**：下载完成后可打开文件、打开目录、复制路径；失败任务可查看原因并快速重试或打开设置
```

- [ ] **Step 5: Commit**

```powershell
git add README.md
```
