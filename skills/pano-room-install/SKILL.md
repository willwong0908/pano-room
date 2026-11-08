---
name: pano-room-install
description: 将环映 360° 全景原画播放器安装或更新到极空间 NAS，通过 Docker Compose 接入影片目录并配置局域网优先连接。用于“安装环映”“部署全景播放器到极空间”等请求。
---

# 环映安装

环映直接读取已拼接的 2:1 全景 MP4/MOV，支持 8K、拖动环视和全屏。视频由播放设备解码。资源在本 Skill 的 assets/runtime，安装只需要这些资源和 scripts/prepare.py。

先确定用户授权的 NAS、影片目录、应用目录及可用端口。极空间路径、账号、IP 来自当前环境，不能照抄其他用户的配置。影片挂载只读，cache 存放目录配置、部署标识、元信息和缩略图。

## 部署

使用可用的极空间连接工具。已有 zspace-nas-agent-toolkit 时先按它的登录和路径规则操作，具体命名命令见 [references/zspace.md](references/zspace.md)。没有该工具时，可使用用户已授权的 NAS SSH 和 Docker Compose。OAuth 登录交给该工具管理。

1. 查询目标 NAS 的个人空间、选中影片目录和端口。极空间文件 API 的虚拟路径需转换为 Docker 可用的原生路径。
2. 用 prepare.py 生成本机暂存目录。--media 可以重复，传用户同意开放给播放器的目录，包含子文件夹。--lan-url 使用 NAS 当前局域网地址及宿主机端口。未提供时继续使用原访问入口。
3. 将暂存目录中的 app/、Dockerfile、LICENSE 和 compose.yaml 上传到独立应用目录。获取该应用目录的 NAS 原生路径。Compose 通过平台创建时，将卷里的 ./app 和 ./cache 改成目标原生绝对路径。
4. 创建 pano-room Compose 项目并启动。端口冲突或已有同名项目时，检查现有项目后调整。默认 ubuntu:24.04 在首次启动时安装 Python/FFmpeg，需要访问 Ubuntu 软件源。也可 --build 后通过具有构建能力的 Docker Compose 执行 up -d --build。
5. 等待健康检查通过，调用 /api/library，确认用户文件的宽高和编码。验证 /source/<id> 的 Range 请求返回 206，并播放一个用户授权的样片。没有可用样片时明确报告此项待验。
6. 极空间远程访问里添加环映，地址设为对应容器入口，发送快捷方式到桌面。打开时会尝试 LAN_URL，核对同一部署标识后自动直连，探测失败继续使用原代理。验证原快捷方式实际导航到内网地址。

~~~sh
python3 scripts/prepare.py \
  --output /临时目录/pano-room \
  --media /已查询的NAS原生影片目录 \
  --lan-url http://NAS内网IP:8765
~~~

## 更新

先检查现有 Compose、挂载和 cache/folders.json。保留用户的目录配置、部署标识和原片，在暂存目录准备更新。替换应用源码并重启对应容器。旧部署使用 m2/sata 目录键时，应在 MEDIA_ROOTS 中保留相同键和容器路径，以兼容现有 folders.json。将现有 LAN_URL、端口与媒体挂载带入新配置。

## 验收边界

局域网优先使用可达性和部署标识判断。同名或相同私网 IP 的其他 NAS 不应触发切换。系统限制局域网请求时会保留代理，手机和 Mac App 应分别验证。

8K HEVC 的解码能力、HDR 显示和网络吞吐取决于客户端。浏览器播放不等于极空间 App 验收。用实际入口测试，报告实际观察到的结果。INSV 原片需先用相机软件导出全景 MP4/MOV。
