# 🎮 游戏文本翻译工具 v4.0

**完全开源免费、无任何功能限制**的游戏文本智能翻译工具。

核心特性：拖入 `.exe` → 自动识别引擎 → 提取文本 → AI 翻译 → **永久注入译文** → 玩家可直接启动已汉化的游戏。
v4.0 升级：CustomTkinter 深色主题 UI + 安全兼容模式 + 强制内存注入 + 断点续传 + 智能错误诊断。

---

## 🚀 快速开始

### 方式一：Python 直接运行

```bash
# 1. 安装依赖（仅需 3 个包）
pip install openai tkinterdnd2 customtkinter

# 2. 启动
python main.py
```

或直接双击 `start.bat`。

### 方式二：打包为独立 .exe（无需 Python 环境）

```bash
# 双击运行 build.bat
# 输出: dist/GameTranslator.exe (~15-20MB 单文件)
```

---

## 📖 使用流程

```
1. 拖入游戏 .exe 到界面中央拖拽区
       ↓
2. 程序自动检测引擎类型（RPG Maker / Ren'Py 等）
       并提取所有可翻译文本
       ↓
3. 配置 API（右上角 ⚙️ 设置）
       ↓
4. 点击「🚀 开始翻译」
       ↓ (进度条实时更新)
5. 翻译完成 → 自动注入译文到游戏文件 + 生成备份
       ↓
6. 点击「▶️ 启动已汉化游戏」 或 直接双击原始 .exe
```

**翻译完成后，译文已永久写入游戏文件。下次玩游戏无需再启动本工具。**

---

## 🎯 支持的引擎

| 引擎 | 支持状态 | 注入方式 |
|------|----------|----------|
| RPG Maker MV | ✅ 完整支持 | 直接覆写 `www/data/*.json`（自动备份） |
| RPG Maker MZ | ✅ 完整支持 | 直接覆写 `data/*.json`（自动备份） |
| Ren'Py | ✅ 完整支持 | 生成 `game/tl/chinese/*.rpy` |
| Unity | ⚠️ 特征检测 | 引导用户使用 AssetStudio 导出后再处理 |
| 通用 JSON/CSV/PO | ✅ 支持 | 遍历 `localization/` `lang/` `i18n/` 目录 |

---

## 🎨 翻译风格控制

内置 5 种风格预设：

| 风格 | 效果 |
|------|------|
| **无特定风格** | 标准游戏本地化 |
| **二次元轻小说风** | 轻松活泼，使用「～」「呢」「嘛」等语气词 |
| **硬核科幻风** | 冷峻精准，术语专业 |
| **信达雅文学风** | 追求文雅优美的文学表达 |
| **热血少年漫风** | 充满力量感的少年漫画风格 |

支持**自定义提示词**（最高优先级），例如：「把语气改得更傲娇一点」「魔法词汇用音译」。

---

## 📖 术语字典 (`dict.json`)

程序同目录下创建 `dict.json`：

```json
{
  "Elixir": "灵药",
  "Goblin": "哥布林",
  "HP": "生命值",
  "Critical Strike": "暴击"
}
```

也可在 GUI 中通过「📖 术语字典」按钮可视化编辑。

---

## 📝 玩家纠错系统

翻译完成后，点击「📝 纠错编辑器」：

- 查看所有原文 ↔ AI 译文对照
- 双击「我的修正」列，直接修改不完美的译文
- 点击「🚀 应用修正并注入游戏」→ 译文立即更新到游戏文件
- **无需重新运行 AI 翻译**，下次启动游戏即可看到修正后的效果

---

## 🔒 五大安全防护

| 机制 | 实现 |
|------|------|
| **本地化优先** | 检测 `localhost`/`127.0.0.1` 时界面显示 🔒 绿色徽章「本地离线模式·数据不出本机」 |
| **零日志无痕** | 绝不记录或上传任何待翻译文本、AI 返回结果到第三方 |
| **禁用危险分享** | 无翻译快照生成、无网页分享、无剪贴板监听、无云端同步 |
| **权限最小化** | 文件操作仅限游戏目录，退出自动清理内存缓存 |
| **密钥加密存储** | XOR 混淆 + Base64 → `config.json` 中仅存储密文 |

---

## 🏗️ 项目架构 (MVC)

```
API UI/
├── main.py                    # 一键启动入口
├── engine/                    # Model 层（业务逻辑）
│   ├── api_client.py          # 统一 API 调度器（兼容 OpenAI / LM Studio / Ollama）
│   ├── prompt_builder.py      # 风格预设 + 术语注入
│   ├── config_manager.py      # 配置持久化（XOR 混淆）
│   ├── glossary_manager.py    # 术语 CRUD
│   ├── backup_manager.py      # 原文件备份保护
│   ├── extractor/             # 引擎识别与文本提取
│   │   ├── detector.py        # 特征文件匹配
│   │   ├── rpgmaker.py        # RPG Maker JSON 递归
│   │   ├── renpy.py           # Ren'Py 正则
│   │   └── generic.py         # JSON/CSV/PO
│   └── injector/              # 译文注入框架
│       ├── rpgmaker_injector.py  # JSON 回写 + 缓存
│       └── renpy_injector.py     # .rpy 翻译生成
├── ui/                        # View + Controller 层
│   ├── main_window.py         # 主窗口
│   ├── settings_dialog.py     # API 设置（含隐私徽章）
│   ├── style_panel.py         # 风格控制面板
│   ├── glossary_editor.py     # 术语编辑器
│   ├── correction_editor.py   # 玩家纠错编辑器
│   └── widgets.py             # 拖拽区 + 进度条
├── utils/                     # 通用工具
│   ├── retry.py               # 通用重试装饰器
│   ├── text_guard.py          # 占位符/乱码检测
│   └── security.py            # 本地检测 + 内存清理
├── start.bat / start.sh       # 一键启动脚本
├── build.bat                  # PyInstaller 打包脚本
└── README.md
```

---

## 🔧 API 兼容性

所有兼容 OpenAI Chat Completions 格式的服务均可使用：

| 服务 | Base URL | 示例 |
|------|----------|------|
| DeepSeek | `https://api.deepseek.com` | 需 API Key |
| OpenAI | `https://api.openai.com/v1` | 需 API Key |
| LM Studio | `localhost:1234` | 无需 API Key |
| Ollama | `localhost:11434` | 无需 API Key |
| vLLM | `localhost:8000` | 无需 API Key |
| 自定义 | 任意 | 按需 |

---

## 📦 PyInstaller 打包

```bash
# 双击 build.bat 即可一键打包
# build.bat 自动执行:
#   1. 检测多版本 Python (py / python / python3)
#   2. 安装 PyInstaller + 所有运行时依赖
#   3. 清理旧构建 + 检测图标 (resources/icon.ico)
#   4. 执行单文件打包 (--onefile --noconsole)

# 输出: dist/GameTranslator.exe
# 体积: ~25-30MB（含 Python + CustomTkinter + tkinter 运行时）
```

打包后的 `.exe` 可独立分发，无需安装任何运行环境。`config.json` 会在 `.exe` 同目录自动生成。

---

## 📋 依赖清单

| 包 | 用途 | 大小 |
|----|------|------|
| `openai` | API 通信 | ~1.5MB |
| `tkinterdnd2` | 文件拖拽 | ~50KB |
| `customtkinter` | 现代化深色主题 GUI | ~2MB |
| 其他均为 Python 内置 | — | — |

### 🛡️ EXE 崩溃保护

打包后的 `.exe` 内置全局异常捕获——即使发生致命错误（如缺少 DLL），也会弹出友好的中文报错提示，而非直接闪退。错误详情自动写入 `error.log`。

---

## ❓ 常见问题

**Q: 误操作导致游戏文件损坏怎么办？**

游戏原始文件自动备份在 `<game_root>/.backup_originals/` 目录。删除修改后的文件，将备份复制回去即可还原。

**Q: 翻译完的游戏可以发给朋友吗？**

可以。译文已永久写入游戏文件，对方无需安装本工具即可游玩汉化版。

**Q: 是否会上传我的游戏文本？**

**绝对不会。** 程序仅向您指定的 API 地址发送翻译请求。如果使用本地模型（LM Studio / Ollama），所有数据完全不出本机。