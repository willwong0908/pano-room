# 环映 · Pano Room

运行在极空间 Docker Compose 中的 360° 全景片库与原画播放器。

支持已拼接的 2:1 全景 MP4/MOV。浏览器和极空间 App 可拖动环视、跳转进度、回正视角和全屏。支持 8K 原画。NAS 按关键帧读取原视频，浏览器边播边预读，可拖动进度、双指缩放；支持的桌面浏览器也可用滚轮缩放。播放设备负责解码，实际流畅度和 HDR 显示取决于设备、浏览器和网络。

访问入口会自动探测配置的 NAS 局域网服务，核对同一部署标识后自动直连。超时或探测受系统限制时继续使用代理。媒体目录只读挂载，目录配置、部署标识、缩略图和元信息保存在 cache 中。

## 交给 Agent 安装

把下面这段话发给支持 Skill 的 Agent。

> 请安装 https://github.com/willwong0908/pano-room/tree/main/skills/pano-room-install 中的 Skill，然后使用它把环映部署到我的极空间。先发现我的 NAS 和影片目录，配置局域网优先连接，并验证真实样片播放。

Codex 用户可通过 skill-installer 安装上面的 GitHub Skill 路径。安装后的调用示例为“使用 $pano-room-install 把环映安装到我的极空间”。

Skill 自带软件源码、部署目录生成脚本和极空间部署指引。操作 NAS 需要可用的极空间连接工具或用户授权的 SSH。推荐配合 zspace-nas-agent-toolkit，授权由其 OAuth 流程完成。

## 让 Agent 更新已有安装
直接告诉 Agent：

> 请检查 https://github.com/willwong0908/pano-room 的 VERSION，与我极空间上环映的 /api/health 版本比较。如果有新版，读取该版本的 skills/pano-room-install/SKILL.md，保留现有影片目录、缓存配置、端口和快捷方式，升级后用我的一段全景视频验证。国内可用 https://gitee.com/willwong0908/pano-room 。

不用 Star、Watch 或重新安装 NAS 应用。旧 Skill 是本地副本，更新时应重新读取仓库同一提交的 Skill 和运行文件。关注仓库不会触发 NAS 自动升级。

## 0.5.1 兼容播放与体感（待更多手机实测）

当视频画面宽高超出设备的 WebGL 单纹理上限时，浏览器会尝试按设备上限缩小全景显示画面；原片仍保持原样，设备仍需解码原始视频。例如 7680×3840 的片源在 4096 上限的设备上尝试以 4096×2048 渲染。是否流畅取决于设备的解码和渲染能力。

播放器左上角的“体感”可开启或关闭设备方向控制。传感器通常要求可信 HTTPS 安全上下文、用户授权，且浏览器或内嵌页面必须允许传感器访问；局域网 HTTP 页面可能无法使用体感，仍可手势环视。兼容路径已用浏览器模拟 4096 上限及方向事件测试，目标手机的真实表现仍待验证。

## 0.5.0 的播放与缓存
支持 HLS.js 的客户端在播放时继续预读，跳转后优先读取新位置附近的片段。预读使用客户端临时空间，剩余容量或浏览器配额不足时可能无法读完整片。返回片库、切换影片或正常离开页面时会尝试释放临时缓存；异常退出可能要等下次打开再清理。原生播放回退时由浏览器管理缓冲。NAS 不生成另一份 8K 视频。

## 国内镜像

国内用户可以从 [Gitee 镜像](https://gitee.com/willwong0908/pano-room) 获取完整源码和安装 Skill：

~~~sh
git clone https://gitee.com/willwong0908/pano-room.git
~~~

把下载后的 skills/pano-room-install 目录交给支持本地 Skill 的 Agent 安装。向 Agent 说明：“请读取这个 Skill，帮我将环映安装到极空间。” Gitee 镜像使用仓库页面上的同步入口更新，可能与 GitHub 有时间差。

## 手动 Docker Compose 部署

需要 Python 3.10+ 生成部署目录，以及 Docker Compose。先查询目标机器上的媒体目录与局域网地址，替换下面的示例值。

~~~sh
git clone https://github.com/willwong0908/pano-room.git
cd pano-room
python3 skills/pano-room-install/scripts/prepare.py \
  --output deployment \
  --media /path/to/panoramas \
  --lan-url http://NAS内网IP:8765
cd deployment
docker compose up -d
~~~

生成目录内包含 app/、compose.yaml、Dockerfile 和许可证。默认使用 ubuntu:24.04，首次启动安装 Python、FFmpeg 和证书，需要访问镜像仓库及 Ubuntu 软件源。FFmpeg 用于元信息和缩略图。提前构建方式使用 --build 生成，再执行 docker compose up -d --build。

--media 可以重复传入多个目录，--port 可更改宿主机端口。LAN_URL 使用对应的宿主机端口。极空间的 /nvmeN/my/data 一类虚拟路径须先转换成 Docker 可用的原生目录。安装助手参考文档给出了命名命令。

打开 http://NAS内网IP:8765。可在“影片文件夹”管理已挂载目录中的文件夹。新增挂载范围需要更新 Compose。

默认提供局域网访问，打开页面即可浏览已挂载影片。公网暴露应按使用者的访问控制要求配置。INSV 原片需先通过 Insta360 Studio 导出 2:1 全景 MP4。步骤见 [Insta360 Studio 导出指引](skills/pano-room-install/references/insta360-export.md)。

## 验证与已有部署更新

~~~sh
python3 -m unittest discover -s tests -v
~~~

本版本在极空间 Z4Pro+ 的现有部署中验证过 X6 7680×3840 HEVC HLG 全景 MP4，以及 Mac 极空间 App 的局域网自动切换。其他设备应通过自己的原片验证解码和网络速度。手机 App 的自动切换需要实机验收。

升级现有部署时保留 cache、端口、LAN_URL 和媒体卷。保留 MEDIA_ROOTS 中原有目录键及容器路径，使 folders.json 继续有效。安装助手使用暂存目录生成配置，检查现有服务后再更新。

## 源码与许可

播放器源码位于 skills/pano-room-install/assets/runtime/app，Go 分段索引器源码和锁定依赖位于 skills/pano-room-install/assets/indexer。Skill 被单独安装时，这些文件会一起携带。prepare.py 复制这些资源并按目标机器生成配置。

AGPL-3.0-or-later。全景投影参考 wizcs/files_360viewer，来源及快照见 NOTICE，许可证见 LICENSE。
