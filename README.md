# 环映 · Pano Room

运行在极空间 Docker Compose 中的 360° 全景片库与原画播放器。

支持已拼接的 2:1 全景 MP4/MOV。浏览器和极空间 App 可拖动环视、跳转进度、回正视角和全屏。视频以原文件通过 HTTP Range 传输，支持 8K，实际解码能力和 HDR 显示取决于播放设备。

访问入口会自动探测配置的 NAS 局域网服务，核对同一部署标识后自动直连。超时或探测受系统限制时继续使用代理。媒体目录只读挂载，目录配置、部署标识、缩略图和元信息保存在 cache 中。

## 交给 Agent 安装

把下面这段话发给支持 Skill 的 Agent。

> 请安装 https://github.com/willwong0908/pano-room/tree/main/skills/pano-room-install 中的 Skill，然后使用它把环映部署到我的极空间。先发现我的 NAS 和影片目录，配置局域网优先连接，并验证真实样片播放。

Codex 用户可通过 skill-installer 安装上面的 GitHub Skill 路径。安装后的调用示例为“使用 $pano-room-install 把环映安装到我的极空间”。

Skill 自带软件源码、部署目录生成脚本和极空间部署指引。操作 NAS 需要可用的极空间连接工具或用户授权的 SSH。推荐配合 zspace-nas-agent-toolkit，授权由其 OAuth 流程完成。

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

默认提供局域网访问，打开页面即可浏览已挂载影片。公网暴露应按使用者的访问控制要求配置。INSV 原片需先通过相机软件导出 2:1 全景 MP4/MOV。

## 验证与已有部署更新

~~~sh
python3 -m unittest discover -s tests -v
~~~

本版本在极空间 Z4Pro+ 的现有部署中验证过 X6 7680×3840 HEVC HLG 全景 MP4，以及 Mac 极空间 App 的局域网自动切换。其他设备应通过自己的原片验证解码和网络速度。手机 App 的自动切换需要实机验收。

升级现有部署时保留 cache、端口、LAN_URL 和媒体卷。保留 MEDIA_ROOTS 中原有目录键及容器路径，使 folders.json 继续有效。安装助手使用暂存目录生成配置，检查现有服务后再更新。

## 源码与许可

软件的唯一源码位于 skills/pano-room-install/assets/runtime/app。Skill 被单独安装时，这些文件会一起携带。prepare.py 复制这些资源并按目标机器生成配置。

AGPL-3.0-or-later。全景投影参考 wizcs/files_360viewer，来源及快照见 NOTICE，许可证见 LICENSE。
