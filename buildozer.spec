[app]

# 应用信息
title = 音频提取器
package.name = audioextractor
package.domain = org.audioextractor

# 版本号（buildozer 必须配置项）
version = 1.1.0

# 源码
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,ffmpeg-arm64,ffmpeg-armv7

# Python 依赖
requirements = python3,kivy,plyer

# 屏幕方向
orientation = portrait

# ======= Android 关键配置 =======
android.api = 33
android.minapi = 21
android.target_sdk = 33
android.archs = arm64-v8a
android.ndk = 25b
android.sdk = 33
android.versioncode = 1
android.version_name = 1.1.0

# 权限
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_AUDIO,READ_MEDIA_VIDEO,MANAGE_EXTERNAL_STORAGE

# 主题和背景
android.apptheme = @style/Theme.AppCompat.NoTitleBar
android.window_background = #141724

# 接受SDK许可
android.accept_sdk_license = True

# 日志过滤
android.logcat_filters = *:S python:D

# p4a 分支（使用稳定版，减少下载量）
p4a.branch = develop

# ======= ffmpeg 资源文件打包 =======
# 打包时将 assets 目录下的 ffmpeg 二进制文件一同打入 APK
# 具体文件在构建前由 Colab 脚本下载放入 assets/bin/
