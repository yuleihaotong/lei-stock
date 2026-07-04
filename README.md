# A股短线决策辅助工具 - 四灯指示系统

基于东方财富公开行情接口的A股分析工具，独创四灯决策指示系统。
**支持两种运行模式：Termux终端版 + Android APK版**

---

## 📱 快速开始 - 下载APK（傻瓜式）

> **如果你只需要安装包，直接下载 APK 即可！**
>
> 1. 在 Releases 页面下载最新的 `.apk` 文件，或使用 `build_apk.sh` 自行构建
> 2. 在Android手机上点击安装（首次需开启"允许安装未知来源应用"）
> 3. 打开应用，自动运行

---

## 🚀 功能特性

### 后端引擎
| 模块 | 功能 |
|------|------|
| **实时行情** | 价格、涨跌幅、成交量、成交额、换手率、振幅等全维度数据 |
| **模糊搜索** | 支持股票名称/代码快速搜索 |
| **技术指标** | MA5/MA10/MA20均线、日涨跌幅、20日波动率、支撑/阻力位 |
| **四灯决策** | 🟢🔴 独创四维度红绿灯决策指示系统 |
| **数据存储** | SQLite持久化自选股、查询记录、设置项 |
| **定时刷新** | 30秒/1分钟/5分钟可选自动刷新 |

### 💡 四灯决策指示系统（核心卖点）

K线图下方四个指示灯，与时间轴对齐，红绿两色直观指示：

| 维度 | 🔴红色（强势/优势） | 🟢绿色（弱势/劣势） |
|------|-------------------|-------------------|
| **区间** | 价格 > MA10 且 处于20日区间中上部 | 价格 < MA10 或 触及区间底部 |
| **走势** | 均线多头排列 或 站稳MA5向上 | 均线空头排列 或 跌破MA5 |
| **板块** | 量比>0.8 且 近3日有2日收阳 | 量能萎缩 且 持续走弱 |
| **量价** | 收阳放量 / 缩量回调（健康） | 放量下跌 / 缩量上涨（背离） |

**决策逻辑：**
- 🔴🔴🔴🔴 **四灯全红 → 可进场** 🚀
- 🟢🔴🔴🔴 **三红一绿 → 谨慎关注** 👀
- 🟢🟢🔴🔴 **二红二绿 → 中性观望** ⚖️
- 🟢🟢🟢🔴 **一红三绿/全绿 → 考虑离场** ⚠️

### 终端UI（Textual模式）
- **首页**：自选股列表 + 大盘概况（上证/深证/创业板指）
- **搜索页**：输入名称/代码实时搜索
- **详情页**：实时行情 + 字符K线图 + 四灯指示 + 指标摘要
- **设置页**：自选股管理 + 刷新间隔设定

### APK模式（WebView界面）
- 移动端优化的触摸友好界面
- WebView加载响应式HTML5页面
- Flask REST API 后台服务
- 自动定时刷新

---

## 📥 安装与运行

### 方式A：直接安装APK（免折腾）

```
1. 下载 APK 文件
2. Android手机安装（允许未知来源）
3. 打开即用，自动刷新行情
```

### 方式B：Termux终端版

```bash
# 1. 更新环境
pkg update && pkg upgrade -y
# 2. 安装Python
pkg install python git -y
# 3. 获取代码
cd ~ && git clone https://github.com/your/stock_tool.git
cd stock_tool
# 4. 安装依赖
pip install -r requirements.txt
# 5. 运行终端版
python main.py
```

### 方式C：Web API模式（开发/调试）

```bash
# 安装带Flask的依赖
pip install -r requirements.txt
# 启动后端API服务
python android/main_android.py
# 浏览器访问 http://127.0.0.1:5000/
```

---

## 📁 项目结构

```
stock_tool/
├── main.py                      # Termux终端版入口
├── app.py                       # Textual应用主框架
├── web_api.py                   # Flask API服务（APK模式）
├── requirements.txt             # 依赖清单
├── README.md                    # 说明文档
├── buildozer.spec               # Buildozer APK打包配置
├── Dockerfile.builder           # Docker构建环境
├── build_apk.sh                 # 一键APK构建脚本
│
├── fetcher.py                   # 🌐 东方财富接口封装
├── analyzer.py                  # 📐 技术指标计算
├── indicator_engine.py          # 💡 四灯决策核心逻辑（APK化时保持不动）
├── database.py                  # 🗄️ SQLite存储
├── scheduler.py                 # ⏱️ 定时调度器
│
├── ui/                          # 终端UI
│   ├── __init__.py
│   └── main_screen.py
│
├── frontend/                    # Web前端（APK用）
│   ├── index.html
│   ├── style.css
│   └── app.js
│
└── android/                     # APK构建资源
    ├── __init__.py
    ├── main_android.py           # Android入口
    ├── StockActivity.java        # WebView Activity
    ├── PythonService.java        # 后台服务
    ├── AndroidManifest.xml       # 清单文件
    └── res/xml/network_security_config.xml
```

---

## 🏗️ 构建APK（开发者）

### 前提条件
- **Linux/Mac**（或Windows WSL2）
- **Docker**（推荐）或手动安装Android SDK

### 一键Docker构建（推荐）

```bash
# 只需要一行命令
./build_apk.sh docker
```

构建过程：
1. 自动拉取Ubuntu 22.04 Docker镜像
2. 安装Python、Java、Android SDK
3. 运行Buildozer打包
4. APK输出到 `bin/` 目录

### 手动构建

```bash
# 安装Buildozer
pip install buildozer cython

# 构建APK
buildozer android debug

# APK位置: bin/stocktool-1.0.0-debug.apk
```

### 构建时间
- 首次构建：30-60分钟（下载Android SDK等）
- 后续构建：5-10分钟

---

## 🔧 技术架构

```
┌─────────────────────────────────────────────────────┐
│                    Android APK                       │
│  ┌─────────────┐    ┌──────────────────────────┐   │
│  │  WebView    │◄──►│  Flask API (127.0.0.1)   │   │
│  │  (HTML/JS)  │    │  ┌────────────────────┐  │   │
│  │             │    │  │  indicator_engine  │  │   │
│  │ 前端界面     │    │  │  fetcher/analyzer  │  │   │
│  │             │    │  │  database/scheduler│  │   │
│  └─────────────┘    │  └────────────────────┘  │   │
│                     └──────────────────────────┘   │
└─────────────────────────────────────────────────────┘
         │
         ▼  HTTP/HTTPS
┌─────────────────────┐
│  东方财富公开API      │
│  (无需Token/登录)    │
└─────────────────────┘
```

### 关键技术决策
| 决策 | 选择 | 原因 |
|------|------|------|
| **APK方案** | Buildozer + Python-for-Android | 成熟稳定，社区活跃 |
| **UI方案** | WebView + Flask API | 与indicator_engine.py解耦 |
| **核心算法** | indicator_engine.py保持纯Python | 可无缝嵌入Chaquopy |
| **数据接口** | 东方财富HTTP API | 免费、无需认证、数据全面 |

### 未来APK化演进
当前 `indicator_engine.py` 设计为纯Python计算逻辑，后续可：
1. 通过 **Chaquopy** 直接嵌入Android（无需Flask中间层）
2. 或使用 **BeeWare** (Toga) 实现原生UI
3. 数据层完全不变，只替换UI层

---

## ⚠️ 注意事项

- 数据来源于东方财富公开接口，仅供学习研究
- 建议刷新间隔 ≥30秒，避免请求过于频繁
- 四灯决策为技术分析参考，不构成投资建议
- 股市有风险，投资需谨慎
