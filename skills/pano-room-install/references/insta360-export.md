# 从 INSV 导出可环视的 MP4

安装完成后主动向用户讲解以下步骤。菜单名称可能随 Insta360 Studio 版本、相机型号和系统变化。

1. 在 Mac 或 Windows 安装并打开 [Insta360 Studio](https://www.insta360.com/download)。将原始素材及同一拍摄片段的配套文件完整保存在同一目录，不要擅自重命名或删除。将全景 INSV 拖入 Studio 的媒体页。
2. 选中并预览素材，确认它是 360° 全景素材，且 Studio 识别了所需的镜头文件。按素材和相机需要检查拼接、陀螺仪与防抖设置。
3. 从媒体页选择导出全景视频，确认导出结果为 MP4、360° 全景，画面比例为 2:1。不要选择将全景重新取景成固定视角的平面视频，也不要选择“视频（源文件）”，后者可能仍输出 INSV。
4. 在素材和 Studio 支持的范围内选择原始或最高可用全景分辨率，例如 7680×3840。分辨率由拍摄模式和版本决定，并非所有原片都有 8K。帧率按原片选择。H.265 通常更省空间，但设备需要支持对应编码与分辨率；可按兼容性选择其他可用编码。
5. 完成导出，将 MP4 放到环映已添加的影片文件夹。刷新片库并打开视频，拖动画面确认能够环视。若看到固定视角，回到 Studio 检查全景导出选项。2:1 画面比例只是辅助检查，不能单独证明视频是正确的 360° 全景。

如果使用项目页，官方指导是在 Studio v5.6.1 及以上版本新建 2:1（360° 全景）项目并导出；项目页和媒体页可选分辨率可能不同。如需最高分辨率，先检查媒体页支持的导出选项。X6 的部分导出选项需要更新版本的 Studio，以官方指南和实际界面为准。

官方参考：
- [VR 全景视频编辑、导出说明](https://onlinemanual.insta360.com/studio/zh-cn/operation_guide/file_management/vr-video-editing)
- [导出画质及参数设置](https://onlinemanual.insta360.com/studio/zh-cn/operation_guide/file_management/exported-parameter)
- [文件导出说明](https://onlinemanual.insta360.com/studio/zh-cn/operation_guide/file_management/file-export)
