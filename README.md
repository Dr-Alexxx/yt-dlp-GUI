# yt-dlp-GUI

一个基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 的 Windows 桌面下载工具。粘贴链接即可下载、选择格式或临时播放，无需使用命令行。

界面由 PyWebview + Vue 3 构建；yt-dlp 通过 Python API 内置在程序中。

## 功能

- **粘贴即下**：支持单个链接和批量链接（每行一个）
- **下载队列**：1-5 个并发任务，显示进度、速度和剩余时间
- **暂停 / 恢复 / 取消 / 重试**：保留 yt-dlp 的断点续传能力
- **格式选择**：按清晰度分组展示 AVC / HEVC / AV1、文件大小和高码率标记，默认推荐兼容性最好的 AVC
- **仅音频与字幕**：下载前按任务选择 MP3、字幕和字幕语言
- **在线播放**：临时下载完成后使用内置播放器播放；关闭播放页或退出应用时自动删除临时文件
- **播放列表选择**：支持勾选想下载的播放列表条目
- **Cookie 支持**：支持 Netscape `cookies.txt` 和 JSON Cookie；可使用系统文件选择器导入
- **Cookie/风控辅助**：浏览器 Cookie 被锁时自动降级；抖音 Fresh cookies 风控自动重试；常见错误提供中文说明
- **自定义 UA**：按任务使用自定义 User-Agent，适合 Cookie 与浏览器指纹需要匹配的站点
- **FFmpeg 管理**：检测系统 FFmpeg；缺失时可下载到应用目录的 `bin\`，不污染系统环境
- **运行状态栏**：主页显示 FFmpeg、Cookie 和内置 yt-dlp 版本状态
- **任务快捷操作**：完成任务可打开文件、打开目录、复制路径；失败任务可查看、复制错误并快速重试
- **下载历史**：任务记录持久化，重启后仍可查看和重试
- **退出保护**：下载或播放进行中时关闭窗口会要求确认

## 快速开始

### 使用 Release（推荐）

1. 下载并解压 Release 压缩包
2. 保留整个 `yt-dlp-GUI` 文件夹
3. 双击 `yt-dlp-GUI.exe`
4. 在“下载”页粘贴链接，点击“添加下载”

程序不需要额外安装 Python。

### 从源码运行

```powershell
git clone https://github.com/Dr-Alexxx/yt-dlp-GUI.git
cd yt-dlp-GUI
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
.venv\Scripts\python app.py
```

开发前端时可另开终端：

```powershell
cd frontend
npm run dev
```

然后使用：

```powershell
.venv\Scripts\python app.py --dev
```

### 自行打包 Windows 程序

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

产物位于：

```text
release\yt-dlp-GUI\yt-dlp-GUI.exe
```

## 使用说明

### 普通下载

1. 粘贴视频链接
2. 根据需要开启“仅音频”或“字幕”
3. 点击“添加下载”
4. 在任务列表查看进度；完成后可直接打开文件或所在目录

“更多下载选项”中可以设置字幕语言和自定义 UA。

### 选择清晰度

点击“解析格式…”后可查看可用格式。

- **AVC / H.264**：兼容性最好，适合默认选择
- **HEVC / H.265**：文件更小，但旧设备可能不支持
- **AV1**：通常体积最小，但需要较新的硬件/播放器
- **高码率**：同一清晰度下画质更高、文件更大，常需要登录会员
- **音频格式**：只下载音频，不包含视频画面

“最佳画质（默认）”会让 yt-dlp 自动选择最高可用且可合并的格式。

### B 站高画质与 Cookie

部分 B 站视频、番剧或会员画质需要登录 Cookie。

1. 登录 bilibili.com
2. 导出 Cookie：可使用 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) 或 [GetCookie](https://github.com/ytdl-patched/GetCookie)
3. 打开“设置”页
4. 点击“浏览…”选择 Cookie 文件
5. 根据文件格式选择 `Netscape (cookies.txt)` 或 `JSON`
6. 保存设置后重新解析链接

Cookie 文件是登录凭证，请勿分享给他人。

### FFmpeg

FFmpeg 用于：

- 合并高清分离视频流和音频流
- 提取 MP3 音频
- 在线播放的临时视频合并

主页状态栏会显示 FFmpeg 是否可用。未就绪时，顶部会提供下载入口；下载后只保存在程序目录的 `bin\` 内。

### 临时播放

点击“解析格式…”后选择“▶ 在线播放”。

播放会先临时下载文件，再通过内置播放器播放。关闭播放页或退出程序时，临时文件会自动删除，不会写入下载历史。

## 常见问题

### 为什么只看到 480P？

通常有两种原因：

1. 未配置有效 Cookie，站点只返回游客画质
2. FFmpeg 未就绪，高画质视频和音频无法合并

先检查主页状态栏中的 Cookie 和 FFmpeg 状态，再重新点击“解析格式…”。

### 任务完成后只有 `.m4a` 音频文件？

FFmpeg 未就绪时，yt-dlp 可能只能保存单独的音频流。安装/检测到 FFmpeg 后重新下载即可。

### 提示“浏览器 Cookie 读取失败”？

浏览器正在运行时，其 Cookie 数据库可能被锁定。程序会尝试以无 Cookie 模式重试；如果需要登录画质，请使用导出的 `cookies.txt` 或 JSON Cookie 文件。

### 提示 HTTP 412 或抖音 Fresh cookies？

这是站点风控提示。建议：

- 重新导出 Cookie
- 使用与导出 Cookie 浏览器一致的 UA
- 降低频繁解析/下载次数后稍后重试

### 番剧能不能选全集？

yt-dlp 可以解析 B 站番剧单集和季页面，但当前 GUI 的番剧季页选集功能仍在后续计划中。普通播放列表可使用现有选集弹窗。

## 项目结构

```text
├─ app.py              # pywebview 入口、JS 桥和退出确认
├─ backend/
│  ├─ api.py           # 前端可调用的 JsApi
│  ├─ downloader.py    # 下载队列、任务状态和 yt-dlp 调用
│  ├─ player.py        # 临时播放会话和本地 Range HTTP 服务
│  ├─ ffmpeg_mgr.py    # FFmpeg 检测与下载
│  ├─ cookies.py       # JSON Cookie 转 Netscape Cookie
│  ├─ errors.py        # 下载错误中文提示
│  ├─ models.py        # 任务状态机
│  └─ config.py        # %APPDATA% 下的配置和任务历史
├─ frontend/           # Vue 3 + Naive UI
├─ tests/              # pytest（74 个用例）
├─ smoke.py            # 无 GUI 下载冒烟脚本
└─ build.ps1           # Windows 一键打包脚本
```

## 开发与验证

```powershell
.venv\Scripts\python -m pytest tests/ -q
.venv\Scripts\python smoke.py
```

技术栈：Python 3.10+、pywebview、yt-dlp、Vue 3、Naive UI、PyInstaller。

## 致谢

本项目的下载能力完全基于开源项目 [yt-dlp](https://github.com/yt-dlp/yt-dlp)。感谢 yt-dlp 社区及所有贡献者，让本项目能够通过一层图形界面覆盖大量视频站点。

前端使用 [Vue 3](https://vuejs.org/) 和 [Naive UI](https://www.naiveui.com/)。

## 免责声明

本项目仅为 yt-dlp 的图形界面封装，仅供个人学习与离线观看使用。请遵守所在地区法律法规及各网站服务条款；下载和使用内容产生的责任由使用者自行承担。

## License

[MIT](LICENSE)
