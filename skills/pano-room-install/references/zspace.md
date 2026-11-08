# 通过 zspace-cli 部署

CLI 来自独立的 zspace-nas-agent-toolkit，按当前环境定位其 scripts/zspace-cli。未安装时可按用户授权安装官方工具包，来源为 https://update.zenithspace.net/app/APP_ZSPACE_NAS_AGENT_TOOLKIT/V0.3.11/zspace/1792998169/zspace-nas-agent-toolkit-0.3.11-thin.zip 。先读取它的 SKILL.md 并遵守完整性校验和 OAuth 流程。

下列 CLI、PROFILE、LOCAL_ROOT 是当前任务变量。命令 JSON 使用脚本或结构化参数生成，避免把路径拼入 shell。所有示例路径都需先查询。

~~~sh
"$CLI" --profile "$PROFILE" file space --params '{}'
"$CLI" --profile "$PROFILE" file list --params '{"path":"目标虚拟目录","num":50}'
"$CLI" --profile "$PROFILE" docker system --params '{"action":"path","path":"目标虚拟目录"}'
"$CLI" --profile "$PROFILE" docker containers --params '{"action":"list"}'
"$CLI" --profile "$PROFILE" docker compose --params '{"action":"list"}'
~~~

确认授权的安装位置后，依次创建应用目录及 app 子目录并上传。上传部署资源，缓存由服务自行创建。upload 对已存在文件默认失败，升级覆盖仅限已确认的目标应用。

~~~sh
"$CLI" --profile "$PROFILE" file mkdir --params '{"parent":"已存在父目录","name":"pano-room"}' --yes
"$CLI" --profile "$PROFILE" --local-root "$LOCAL_ROOT" file upload --params '{"local_path":"app/server.py","dest_path":"目标应用虚拟路径/app/server.py"}' --yes
~~~

通过 docker system path 取得原生路径后，生成最终 Compose。API create 的 path 使用查询确认的应用目录，config 是完整 Compose 文本。

~~~json
{"action":"create","project_name":"pano-room","path":"目标应用目录","config":"完整 Compose 文本","start":true,"pull":true}
~~~

该 JSON 作为 docker compose 的 --params，写入传 --yes。返回任务不等于成功，应查任务及容器。

~~~json
{"action":"task","task_id":"返回的任务ID"}
{"action":"containers","project_id":"返回的项目ID"}
{"action":"logs","project_id":"返回的项目ID"}
~~~

自定义入口/桌面快捷方式未由当前工具提供完整命名能力，可通过极空间 App 的“远程访问 → 新建”操作，填实际端口，并发送快捷方式到桌面。网页源地址可能是 App 的 127.0.0.1 本机转发，环映会自动探测 NAS 局域网服务。
