# yt-dlp GUI 壳子 — 设计文档

日期：2026-09-04
状态：已与用户逐节确认

## 1. 目标与范围

为 yt-dlp 构建一个**自用**的全功能 GUI 壳子：粘贴 URL 即可下载，支持格式选择、下载队列、历史记录、cookie/登录、字幕、音频提取、批量粘贴、播放列表选择，并内置 FFmpeg 下载管理。

**非目标**（YAGNI）：
- 不做打包分发 / 自动更新（自用工具，直接源码运行）
- 不做前端自动化测试
- 不做远程访问 / 多用户

## 2. 技术选型（已确认）

| 层 | 选择 | 理由 |
|---|---|---|
| 窗口/桥接 | pywebview（JS API 桥，方案 A） | 轻量、系统 WebView 渲染、Python 后端直接 `import yt_dlp`，单进程零额外依赖 |
| 前端 | Vue 3 + Vite + Naive UI | 组件库开箱即用，界面精细 |
| 下载核心 | yt-dlp Python API（非 subprocess） | 进度 hook、格式元数据、暂停(断点续传)控制最精细 |
| FFmpeg | 应用目录内置管理 | 不污染系统环境 |

## 3. 目录结构

```
E:\videodown\
├─ app.py              # 入口：创建窗口、加载 dist/、注册 js_api
├─ backend/
│  ├─ api.py           # JsApi 类：前端可调用的所有方法（薄层，只做参数校验和转发）
│  ├─ downloader.py    # DownloadManager：任务队列 + 线程池，唯一和 yt_dlp 打交道的地方
│  ├─ ffmpeg_mgr.py    # FFmpeg 检测与下载管理
│  ├─ models.py        # Task 数据类：id、url、状态、进度、速度、错误信息
│  └─ config.py        # 配置读写（JSON 存 %APPDATA%）
├─ frontend/           # Vue 3 + Vite + Naive UI 项目
└─ dist/               # frontend build 产物，pywebview 加载它
```

## 4. 模块职责

### api.py（JsApi）
前端调用入口，不写业务逻辑。方法清单：
- `add_task(url, options) -> {ok, task_id}`
- `pause_task(id)` / `resume_task(id)` / `cancel_task(id)` / `retry_task(id)`
- `get_task_list()` — 全量拉取（窗口刷新/重开后恢复展示）
- `probe_url(url)` — extract_info 拿标题/封面/可用格式/播放列表条目
- `submit_format_choice(task_id, format_id)` / `submit_playlist_selection(task_id, entries)` — 回传用户选择
- `save_config(...)` / `get_config()`
- `download_ffmpeg()` — 触发 FFmpeg 下载

统一返回格式 `{ok: bool, error?: str}`；非法参数（url 为空、task_id 不存在）在此层拦截，前端 toast 提示。

### downloader.py（DownloadManager）
- 内部 `queue.Queue` + 2~3 个 worker 线程并发下载
- 每个任务创建 `YoutubeDL(options)`，注册 `progress_hook` 抓 percent/speed/ETA
- 通过 `webview.windows[0].evaluate_js(...)` 向前端推送任务状态变化
- **暂停**：yt-dlp 无原生暂停，实现为"取消 + 保留 .part 文件断点续传"；恢复即重新入队
- 拼装 yt-dlp options 时统一注入 `ffmpeg_location`（见 §7）
- 失败自动重试 1 次（网络抖动兜底）

### models.py / config.py
纯数据、无副作用，方便单测。Task 状态机：
`queued → probing → (waiting 用户选格式/播放列表) → downloading → done | error`
任何状态可 → cancelled；error/Cancelled 可 retry（重新入队）。

## 5. 数据流（一次下载的生命周期）

```
前端粘贴 URL → api.add_task(url, options)
  → DownloadManager 入队，Task=queued，立即返回 task_id
  → worker 取任务 → Task=probing，extract_info(noplaylist=True) 拿标题/格式
  → 需用户选择格式/播放列表项时：evaluate_js 推前端，Task=waiting，等前端回传选择
  → Task=downloading，progress_hook 每次 evaluate_js 推 {id, percent, speed, eta}
  → 完成：Task=done，推最终文件路径；失败：Task=error，推错误摘要
```

前端是唯一的状态展示方，后端维护权威 Task 列表；前端启动/刷新时调 `get_task_list()` 全量拉取，之后靠推送增量更新。

## 6. 错误处理

- **yt-dlp 异常**：worker 整体 try/except；`DownloadError` 提炼成一句人话（"视频不可用/需要登录"）推前端，任务标记 error，可一键重试（.part 续传）。
- **网络中断**：yt-dlp 自带 retries + 断点续传；manager 层自动重试 1 次。
- **非法参数**：api.py 校验，统一 `{ok:false, error}`，前端 toast。
- **FFmpeg 缺失**：不阻塞启动，前端横幅提示并可一键下载（见 §7）。
- **退出时任务进行中**：窗口关闭事件询问"有任务进行中，确定退出？"，确认后取消全部任务再退出。

## 7. FFmpeg 内置管理（ffmpeg_mgr.py）

检测顺序（启动时执行）：
1. `config.ffmpeg_path`（用户手动指定）
2. `<应用目录>/bin/ffmpeg.exe`（已内置下载）
3. `shutil.which("ffmpeg")`（系统 PATH）

三者皆无：**不阻塞启动**，前端顶部横幅提示"FFmpeg 未就绪，音频提取/合并不可用"，点击调 `api.download_ffmpeg()`：
- 后台线程从 **BtbN GitHub Releases** 下载 `ffmpeg-master-latest-win64-gpl.zip`（约 90MB，静态链接无依赖）
- 下载进度经 evaluate_js 推到前端横幅
- 解压出 `ffmpeg.exe` + `ffprobe.exe` 到 `<应用目录>/bin/`，删除 zip，路径写入 config
- 中断/失败可重试；已存在则跳过
- DownloadManager 注入 `ffmpeg_location` 指向应用目录 bin/

系统环境零污染；卸载 = 删应用目录。

## 8. 全功能落位

| 功能 | 实现点 |
|---|---|
| 格式选择 | probe_url 返回格式列表 → 前端选择 → submit_format_choice |
| 下载队列 | DownloadManager 队列 + 状态展示 |
| 历史记录 | Task 列表持久化为 JSON，存在 %APPDATA% 下与 config 同目录 |
| cookie/登录 | 设置页配 cookiefile 路径或浏览器名（cookiesfrombrowser） |
| 字幕 | options 写 subtitleslangs / writesubtitles |
| 音频提取 | postprocessor FFmpegExtractAudio（依赖内置 FFmpeg） |
| 批量粘贴 | 前端按行拆分，循环调 add_task |
| 播放列表选择 | probe_url 返回 playlist entries → 前端勾选 → submit_playlist_selection |

## 9. 测试策略

- **单测（pytest）**：models.py、config.py 全覆盖；downloader.py 用 fake yt_dlp（只模拟 progress_hook 调度与 extract_info）测队列调度、暂停/取消/重试状态机；api.py 用 fake manager 测参数校验分支。
- **真实下载不进单测**：留手动冒烟脚本 `smoke.py`，下载一个公开小视频验证全链路。
- **前端**：不做自动化测试（YAGNI），靠冒烟验证。
