# 在线播放（临时流媒体）— 设计文档

日期：2026-09-07
状态：已与用户逐节确认
父项目：yt-dlp-GUI（见 2026-09-04-ytdlp-gui-design.md）

## 1. 目标与范围

为 yt-dlp-GUI 新增"在线播放"功能：粘贴链接后不进下载队列，临时下载到缓存目录后用应用内置播放器播放；关闭播放即删除临时文件。适用于 yt-dlp 支持的所有站点（B 站番剧含大会员内容由用户 cookie 决定）。

**非目标**（YAGNI）：
- 不做播放列表连续播放、倍速记忆、弹幕
- 不做局域网共享（HTTP 服务只绑 127.0.0.1）
- 不做下载任务与播放任务的互通（播放任务不进下载历史）
- 不做外部播放器调用

## 2. 技术选型（已确认）

| 项 | 选择 |
|---|---|
| 播放范围 | yt-dlp 支持的全站通用 |
| 播放器 | 应用内置 HTML5 `<video>`（pywebview WebView2 原生支持） |
| 视频供给 | 本地 HTTP 服务（ThreadingHTTPServer，127.0.0.1 随机端口，支持 Range/206） |
| 临时文件 | `%TEMP%\yt-dlp-gui-play\<session_id>\`，关闭即删 + 启动清扫 |
| 格式 | `bestvideo*+bestaudio/best`（与下载默认一致，需 FFmpeg 合并） |

## 3. 入口与用户流程

1. 任务页「解析格式…」对话框中，"开始下载"按钮旁新增 **"▶ 在线播放"** 按钮
2. 点击 → `api.start_play(url, options)`（options 含 cookie 上下文与自定义 UA，见 §5）→ 前端切换到播放页
3. 播放页三态：
   - **进度态**：显示临时下载进度（百分比/速度），数据来自推送事件
   - **播放态**：下载完成后前端收到事件，`<video>` 指向 `http://127.0.0.1:<port>/<文件名>` 自动播放
   - **错误态**：下载失败显示人话化错误 + "返回"按钮
4. 播放页顶部"关闭并删除"按钮 → `api.stop_play(session_id)` → 返回任务页
5. 应用退出：播放会话视为活跃任务，纳入"有任务进行中"退出确认；确认后统一清理

## 4. 后端设计

### 4.1 新增模块 backend/player.py

```python
class PlayerSession:        # 单次播放会话
    start(url, options, push_event)   # 创建临时目录、起下载线程
    stop()                            # 终止下载、关 HTTP 服务、删临时目录

class PlayerManager:        # 管理会话（当前设计允许同时只开一个播放页，
    start_play(...) -> dict # 多开属 YAGNI，但接口按 dict 会话表实现以便扩展）
    stop_play(session_id)
    cleanup_all()               # 启动时清扫 %TEMP%\yt-dlp-gui-play\ 整个目录
    has_active() -> bool        # 供退出确认使用
```

- 下载线程：`yt_dlp.YoutubeDL` 参数与下载共用组装逻辑（cookie / cookie_file_format / 自定义 UA），`outtmpl` 指向临时目录，`progress_hooks` 推 `{type: "play_progress", percent, speed}`
- 完成事件：`{type: "play_ready", session_id, port, filename}`；失败事件：`{type: "play_error", session_id, error}`（error 经 humanize_error）
- 番剧/大会员支持来自 yt-dlp 的 `BiliBiliBangumiIE`，无需额外代码

### 4.2 Range 支持（backend/player.py 内 handler）

自定义 `BaseHTTPRequestHandler` 子类：
- 解析 `Range: bytes=start-end`，返回 **206** + `Content-Range`；无 Range 返回 200
- 只允许访问会话临时目录内的文件（拒绝 `..` 路径穿越）
- 服务绑定 `127.0.0.1`，端口由系统分配（`ThreadingHTTPServer(("127.0.0.1", 0), ...)`）

### 4.3 生命周期

- `stop_play`：设置取消标志（下载线程在 progress_hook 检查，同下载任务的 DownloadCancelled 机制）→ `server.shutdown()` → 递归删除临时目录
- `cleanup_all`：在 app.py 启动时（创建窗口前）删除 `%TEMP%\yt-dlp-gui-play\` 整个目录（处理上次异常退出残留）
- `app.py`：`main()` 里创建 PlayerManager 并接入 push 事件与退出确认（`has_active()`）

## 5. 与现有模块的交互

| 现有模块 | 交互方式 |
|---|---|
| config / cookies.py | 读取 cookie_file、cookie_file_format、cookies_browser；JSON 转换复用 resolve_cookie_file |
| downloader 的 UA 逻辑 | 播放是独立会话，自定义 UA 以 options（custom_ua/ua_string）形式传入 start_play，组装逻辑保持各自独立（不强行抽公共层，避免过度抽象） |
| errors.py | 下载失败信息统一过 humanize_error；"Fresh cookies"自动重试机制**不适用于播放**（播放线程失败即报错，用户直接重新点播放） |
| frontend store | 新增 `playerSession`（id/port/filename/progress/error/status） |

## 6. 前端设计

- 新组件 `frontend/src/views/PlayerView.vue`：三态渲染（进度 / 播放 / 错误）
- `FormatDialog.vue`：新增"▶ 在线播放"按钮 → `call('start_play', url, options)` → 切视图
- `App.vue`：视图路由加 `player`；播放期间侧边栏菜单**置灰禁用**（点了菜单先自动 `stop_play` 清理会话再切换，防止泄漏会话）
- `store.js`：`playerSession` 状态 + `play_progress/play_ready/play_error` 事件处理

## 7. 错误处理

- FFmpeg 未就绪：前端"在线播放"按钮禁用（tooltip 提示），后端二次校验并返回 `{ok:false, error}`
- 下载失败：play_error 事件，播放页错误态展示 humanize 信息
- 端口/服务异常：start_play 返回 `{ok:false}`
- 临时目录删除失败（文件占用）：记录并跳过，启动清扫时兜底重删

## 8. 测试策略

- **单测（pytest）**：
  - Range handler：真实起服务 + urllib 带/不带 Range 头请求，断言 206/200 与内容区间
  - 路径穿越防护：`GET /..%2f..%2fxxx` 返回 404
  - PlayerSession 生命周期：临时目录创建 → stop 后目录被删除
  - cleanup_all：预置残留目录 → 启动清扫后不存在
  - 接口契约：start_play 未装 FFmpeg 时返回 ok:false
- **真实 yt-dlp 不进单测**：沿用 smoke 思路，手动冒烟
- **前端**：按项目惯例不写自动化测试，构建 + 冒烟

## 9. 实施期偏差记录

- FFmpeg 门禁的前端表现：spec §7 写"按钮禁用 + tooltip"，实施为按钮始终可点、失败时 toast 提示（后端二次校验兜底）
- play_progress 事件未实现 speed 字段（播放页进度仅显示百分比）
