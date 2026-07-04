# =============================================================================
# buildozer.spec - Buildozer APK打包配置文件
# 用于将Python项目打包为Android APK
# 使用方法: buildozer android debug
# =============================================================================

[app]

# 应用标识
title = A股短线决策工具
package.name = stocktool
package.domain = com.stocktool

# 源码目录
source.dir = .

# 入口文件
source.main_ext = py
source.main = android/main_android.py

# 版本
version = 1.0.0
version.regex = __version__\s*=\s*['"](.*?)['"]
version.filename = %(source.dir)s/main.py

# 权限
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE
android.api = 31
android.minapi = 21
android.sdk = 33
android.ndk = 23b
android.gradle_dependencies = 'androidx.webkit:webkit:1.6.1'

# 编译选项
android.arch = arm64-v8a
android.accept_sdk_license = True
android.wakelock = True
android.used_libs = webview

# Java类
android.add_src =

# 图标
icon.filename = android/app_icon.png
# （可选）presplash.filename = %(source.dir)s/android/splash.png

# 需求
requirements = python3, flask, flask-cors, requests

# 正则排除
source.include_exts = py,png,jpg,jpeg,gif,html,css,js,xml,json,txt
source.exclude_exts = spec,md,pyc
source.exclude_dirs = tests, bin, obj, __pycache__, .git

# 日志
log_level = 2
log.filter =

# 存储
android.copy_libs = 1
android.ndk_path =

# 启动画面
presplash.filename = 
presplash.color = #0d1117

# 调试模式
debug = 1


[buildozer]

# 下载目录
download.location = ~/.buildozer

# 编译目录
build.directory = ./buildozer_build

# WARN等级
warn_on_root = 1


# =============================================================================
# p4a (python-for-android) 额外配置
# =============================================================================

[p4a]

# 需要链接的库
libraries = 
# 额外的Java依赖
extra_jars = 
# 额外的assets目录
extra_assets = frontend
