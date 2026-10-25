# 中文编辑器

一个**用中文写代码**的 Python 编程环境（IDE）。把 Python 关键字换成中文，让你用母语编程。

基于 Python + Tkinter 开发，已打包为独立 exe —— **目标电脑不需要安装 Python**，拷走即用。

## ✨ 功能

- **中文编程**：`输出()` 代替 `print()`，`输入()` 代替 `input()`，关键字自动高亮补全
- **内置控制台**：多开 / 关闭终端，`+` / `-` 调整大小，支持 **CMD** 和 **PowerShell** 两种终端
- **代码编辑**：中文关键字高亮、行号、语法检查
- **模块导入补全**：输入 `导入` 自动补全 `import` 语句，并列出已安装的模块
- **模板系统**：一键生成 Flask、SQLite 等常用模板（可改端口、支持局域网访问）
- **文件关联**：`.cnpy` 文件双击用中文编辑器打开，自动换图标
- **安装程序**：检测重复安装、创建桌面/开始菜单快捷方式、一键卸载（bat）

## 🔤 中文 → Python 对照表

写代码时，中文会自动替换成对应的 Python 单词。对照表如下：

### 关键字

| 中文 | Python |
|---|---|
| `否则如果` | `elif` |
| `定义` | `def` |
| `类` | `class` |
| `如果` | `if` |
| `否则` | `else` |
| `对于` | `for` |
| `当` | `while` |
| `返回` | `return` |
| `导入` | `import` |
| `从` | `from` |
| `作为` | `as` |
| `尝试` | `try` |
| `除了` | `except` |
| `最终` | `finally` |
| `抛出` | `raise` |
| `跳过` | `pass` |
| `中断` | `break` |
| `继续` | `continue` |
| `全局` | `global` |
| `删除` | `del` |
| `断言` | `assert` |
| `真` | `True` |
| `假` | `False` |
| `无` | `None` |
| `且` / `并且` | `and` |
| `或` / `或者` | `or` |
| `非` | `not` |
| `在` | `in` |
| `是` | `is` |

### 内置函数

| 中文 | Python |
|---|---|
| `输出` / `打印` | `print` |
| `长度` | `len` |
| `范围` | `range` |
| `输入` | `input` |
| `整数` | `int` |
| `小数` | `float` |
| `字符串` | `str` |
| `布尔` | `bool` |
| `列表` | `list` |
| `字典` | `dict` |
| `集合` | `set` |
| `元组` | `tuple` |
| `类型` | `type` |
| `求和` | `sum` |
| `最大` | `max` |
| `最小` | `min` |
| `排序` | `sorted` |
| `打开` | `open` |
| `绝对值` | `abs` |
| `四舍五入` | `round` |
| `枚举` | `enumerate` |

### 比较与运算

| 中文 | Python |
|---|---|
| `设为` | `=` |
| `等于` | `==` |
| `不等于` | `!=` |
| `大于` | `>` |
| `小于` | `<` |
| `大于等于` | `>=` |
| `小于等于` | `<=` |
| `并且` / `且` | `and` |
| `或者` / `或` | `or` |

### 全角标点自动转换

中文输入法打出的全角标点会自动转成半角：`（）：，。；【】｛｝？！＝＞＜＃％＊＋－＿｜＼＾～＂＇` 等一键转成英文标点；中文弯引号 `“”‘’` 自动当字符串引号使用，写字符串不用切换输入法。

## 📸 实机演示

![浅色界面](https://cdn.jsdelivr.net/gh/huang-dev-lab/cnpy-editor@main/assets/screenshots/demo1-light.png)

![运行效果](https://cdn.jsdelivr.net/gh/huang-dev-lab/cnpy-editor@main/assets/screenshots/demo2-run.png)

![深色主题](https://cdn.jsdelivr.net/gh/huang-dev-lab/cnpy-editor@main/assets/screenshots/demo3-dark.png)

## 🚀 快速开始

### 方式一：下载 exe（推荐）

从 **Releases** 页面下载最新版：

| 文件 | 说明 |
|---|---|
| `cnpy-editor.exe` | 免安装版，双击即用 |
| `cnpy-editor-setup.exe` | 安装版：自动建快捷方式、关联 .cnpy 文件 |

### 方式二：从源码运行

需要 Python 3.10+：

```bash
python src/中文编辑器.py
```

## 🛠️ 从源码构建 exe

需要 PyInstaller：

```bash
pip install pyinstaller
pyinstaller --noconfirm specs/中文编辑器.spec
pyinstaller --noconfirm specs/中文编辑器安装程序.spec
```

产物在 `dist/` 目录。

## 📂 项目结构

```
中文编辑器_python/
├── src/        # 代码：主程序、安装程序、卸载脚本
├── assets/     # 图标（.ico / .png）与演示截图（screenshots/）
├── specs/      # PyInstaller 打包配置（.spec）
├── tools/      # 辅助脚本（文件关联、快速启动）
└── dist/       # 打包产物（exe）
```

## 🧪 示例

```python
名字 = 输入("你叫什么名字？")
输出("你好，" + 名字 + "！")
```

## 📄 许可证

[MIT](LICENSE) © 2026 黄帅钧
