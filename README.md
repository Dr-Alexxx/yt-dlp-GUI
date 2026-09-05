# yt-dlp 下载器

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 的 Windows 桌面 GUI 下载器。粘贴链接即可下载，无需命令行。PyWebview + Vue 3 构建，yt-dlp 以 Python API 方式内置，开箱即用。

## 功能

- **粘贴即下**：单个链接或批量粘贴（每行一个）
- **下载队列**：多任务并发（1~5 可调），实时进度 / 速度 / 剩余时间
- **暂停 / 恢复 / 取消 / 重试**：基于 yt-dlp 断点续传（`.part` 文件）
- **格式选择**：内置解析预览，可指定清晰度；也可直接「仅音频 (MP3)」
- **播放列表选择**：解析播放列表后勾选想要的单集
- **Cookie 支持**：Netscape `cookies.txt` 或 JSON 格式均可（B 站 1080P 等登录画质需要）
- **字幕下载**：按语言逗号分隔配置
- **内置 FFmpeg 管理**：首次使用时自动下载到应用目录的 `bin\`，不污染系统环境
- **下载历史**：任务记录持久化，重启后可查看和重试
- **退出保护**：有任务进行中时关闭窗口会弹确认

## 运行环境

- Windows 10/11（64 位）
- 无需安装 Python 或任何依赖——直接使用 Release 中的构建产物

## 快速开始

### 方式一：直接使用（推荐）

1. 下载 / 构建后将整个 `yt-dlp下载器` 文件夹放到任意位置
2. 双击 `yt-dlp下载器.exe`
3. 粘贴视频链接，点「添加下载」

### 方式二：从源码运行

```powershell
git clone <repo-url>
cd <repo-dir>
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
.venv\Scripts\python app.py          # 生产模式（加载 dist/）
.venv\Scripts\python app.py --dev    # 开发模式（连接 Vite 热更新）
```

开发前端时另开一个终端：`cd frontend && npm run dev`

### 方式三：自己打包 Windows 程序

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

产物在 `release\yt-dlp下载器\`，整个文件夹拷到其他 Windows 电脑可直接使用。

## 使用说明

### 下载 B 站 1080P（登录画质）

1. 登录 bilibili.com
2. 导出 cookies：浏览器扩展 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)，或 [GetCookie](https://github.com/ytdl-patched/GetCookie) 工具
3. 设置页 →「Cookie 文件路径」→「浏览…」选中文件 →「Cookie 文件格式」选对应格式（txt 选 Netscape / json 选 JSON）→ 保存

设置页的「如何导入 Cookie？」折叠面板有完整说明。

### 关于 FFmpeg

音频提取（仅音频 MP3）和高清视频合并需要 FFmpeg。应用首次检测不到时会显示横幅，点击「自动下载到应用目录」即可（约 90MB，来自 [BtbN Builds](https://github.com/BtbN/FFmpeg-Builds/releases)），只写入程序目录的 `bin\`，卸载删文件夹即净。

## 常见问题

**Q: 任务显示完成，但只有 `.m4a` 音频文件？**
FFmpeg 未就绪，无法合并视频+音频流。点横幅下载 FFmpeg 后重新下载即可。

**Q: 提示「浏览器 Cookie 读取失败」？**
所选浏览器正在运行，Cookie 数据库被锁。应用会自动改用无 Cookie 模式重试；如需登录画质，请改用 cookies.txt 文件方式。

**Q: 提示「被网站风控拦截（HTTP 412）」？**
从浏览器直接导出的 Cookie 请求特征可能触发 B 站风控。建议使用 cookies.txt 文件方式，或无 Cookie 模式。

**Q: 下载目录在哪？**
默认 `C:\Users\<用户>\Downloads`，可在设置页修改。

## 项目结构

```
├─ app.py              # 入口：pywebview 窗口、JS 桥、关闭确认
├─ backend/
│  ├─ api.py           # JsApi：前端可调用方法（校验 + 转发）
│  ├─ downloader.py    # DownloadManager：队列 + worker 线程 + yt-dlp 调用
│  ├─ ffmpeg_mgr.py    # FFmpeg 检测与自动下载
│  ├─ cookies.py       # JSON Cookie → Netscape 转换
│  ├─ errors.py        # 常见下载错误的人话化提示
│  ├─ models.py        # Task 状态机
│  └─ config.py        # 配置与任务历史持久化（%APPDATA%\yt-dlp-gui）
├─ frontend/           # Vue 3 + Naive UI（Vite 构建）
├─ tests/              # pytest（50 个用例）
├─ smoke.py            # 无 GUI 全链路冒烟：python smoke.py [url]
└─ build.ps1           # 一键打包脚本
```

## 开发

```powershell
.venv\Scripts\python -m pytest tests/ -q   # 运行全部测试
.venv\Scripts\python smoke.py [url]        # 无 GUI 冒烟验证
```

技术栈：Python 3.10+ / pywebview / yt-dlp（Python API 直接调用，非子进程）/ Vue 3 + Naive UI / PyInstaller。

## 免责声明

本项目仅为 yt-dlp 的图形界面封装，仅供个人学习与离线观看使用。下载内容请遵守所在地区法律法规及各网站服务条款，由此产生的一切问题由使用者自行承担。

## License

[MIT](LICENSE)
