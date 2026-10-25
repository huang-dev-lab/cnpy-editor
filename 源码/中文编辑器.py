# -*- coding: utf-8 -*-
"""
中文编辑器 —— 基于 Python Tkinter 的简单中文文本编辑器
========================================================
功能：
  · 新建 / 打开 / 保存 / 另存为
  · 自动识别文件编码（UTF-8 / GBK / GB18030），可手动切换
  · 撤销 / 重做 / 剪切 / 复制 / 粘贴 / 全选 / 插入日期时间
  · 查找 / 替换 / 全部替换（循环查找）
  · 行号显示、字数统计、状态栏、字号缩放
  · Python 语法高亮（关键字 / 内置函数 / 字符串 / 注释 / 数字 / 函数名）
  · 中文编程：输出() 等价于 print()，定义 等价于 def，自动转换全角标点
  · 一键运行中文代码（F5），内置运行结果面板，可交互输入
  · 导入自动补全：敲 导入 / import 后列出已安装模块，Tab 或 Enter 确认
  · 成员级补全：从 flask 导入 / from sqlite3 import 时列出模块内成员
  · Flask / SQLite 常用代码模板一键插入（中文编程，可直接运行）

运行：python 中文编辑器.py
依赖：仅 Python 标准库（tkinter），无需安装任何第三方包
"""

import codecs
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "中文编辑器"
APP_VERSION = "1.0"
DEFAULT_SIZE = (1180, 780)      # 默认窗口大小
MIN_SIZE = (760, 480)           # 窗口最小尺寸
FONT_FAMILY = "Microsoft YaHei"  # 微软雅黑，中文显示效果较好
FONT_SIZE = 13                   # 默认字号
LINE_NUM_WIDTH = 58              # 行号区域初始宽度（像素）

# 常见的几种文件编码，按优先级尝试解码
ENCODINGS = ["utf-8", "gbk", "gb18030"]

# ---- Python 语法高亮配色（浅色主题，只改颜色不改字体） ----
HL_COLOR = {
    "hl_kw": "#0066cc",        # 关键字：蓝
    "hl_builtin": "#9b59b6",   # 内置函数：紫
    "hl_string": "#0a7d33",    # 字符串：绿
    "hl_comment": "#8a8a8a",   # 注释：灰
    "hl_number": "#d35400",    # 数字：橙
    "hl_funcname": "#2c7da0",  # 函数名 / 类名：青
}

# ---- 主题（浅色 / 深色）----
THEMES = {
    "浅色": {
        "editor_bg": "#ffffff", "editor_fg": "#1a1a1a",
        "line_bg": "#f4f4f4", "line_fg": "#8a8a8a",
        "status_bg": "#e6e6e6", "status_fg": "#333333",
        "root_bg": "#f0f0f0",
        "hl": dict(HL_COLOR),
    },
    "深色": {  # 参考 VSCode Dark+ 配色
        "editor_bg": "#1e1e1e", "editor_fg": "#d4d4d4",
        "line_bg": "#252526", "line_fg": "#858585",
        "status_bg": "#2d2d2d", "status_fg": "#cccccc",
        "root_bg": "#252526",
        "hl": {
            "hl_kw": "#569cd6", "hl_builtin": "#c586c0",
            "hl_string": "#ce9178", "hl_comment": "#6a9955",
            "hl_number": "#b5cea8", "hl_funcname": "#4ec9b0",
        },
    },
}

# 关键字与内置函数表（都是 Python 常用词）
HL_KEYWORDS = (
    "def class if elif else for while return import from as with try except "
    "finally raise pass break continue lambda yield global nonlocal del assert "
    "in is and or not None True False"
).split()
HL_BUILTINS = (
    "print len range input int float str bool list dict set tuple type sum max "
    "min sorted open abs all any enumerate filter map round isinstance id repr "
    "exit help"
).split()

# ---- 中文编程：中文词 → 英文 Python（替换时按词长度从长到短，避免子词误伤） ----
CN_MAPPING = {
    # 关键字
    "否则如果": "elif", "定义": "def", "类": "class", "如果": "if",
    "否则": "else", "对于": "for", "当": "while", "返回": "return",
    "导入": "import", "从": "from", "作为": "as", "尝试": "try",
    "除了": "except", "最终": "finally", "抛出": "raise", "跳过": "pass",
    "中断": "break", "继续": "continue", "全局": "global", "删除": "del",
    "断言": "assert", "真": "True", "假": "False", "无": "None",
    "且": "and", "或": "or", "非": "not", "在": "in", "是": "is",
    # 内置函数
    "打印": "print", "输出": "print", "长度": "len", "范围": "range", "输入": "input",
    "整数": "int", "小数": "float", "字符串": "str", "布尔": "bool",
    "列表": "list", "字典": "dict", "集合": "set", "元组": "tuple",
    "类型": "type", "求和": "sum", "最大": "max", "最小": "min",
    "排序": "sorted", "打开": "open", "绝对值": "abs", "四舍五入": "round",
    "枚举": "enumerate",
    # 比较 / 运算
    "不等于": "!=", "大于等于": ">=", "小于等于": "<=", "等于": "==",
    "大于": ">", "小于": "<", "并且": "and", "或者": "or", "设为": "=",
}
# 按中文词长度降序，保证"否则如果"先于"否则"被处理
CN_MAPPING_SORTED = sorted(CN_MAPPING.items(), key=lambda kv: len(kv[0]), reverse=True)

# 全角标点 → 半角（代码区内转换，字符串和注释里不动）
PUNCT_TRANS = str.maketrans({
    "（": "(", "）": ")", "：": ":", "，": ",", "。": ".", "；": ";",
    "【": "[", "】": "]", "｛": "{", "｝": "}", "　": " ", "？": "?",
    "！": "!", "＝": "=", "＞": ">", "＜": "<", "＃": "#", "％": "%",
    "＊": "*", "＋": "+", "－": "-", "＿": "_", "｜": "|", "＼": "\\",
    "＾": "^", "～": "~", "＂": '"', "＇": "'",
    # 中文弯引号（输入法默认打出的是“ ” ‘ ’，直接当成字符串引号）
    "“": '"', "”": '"', "‘": "'", "’": "'",
})

# ---- 成员补全：动态导入失败时的兜底常用成员表 ----
PRESET_MEMBERS = {
    "flask": [
        "Flask", "request", "jsonify", "render_template", "redirect",
        "url_for", "session", "flash", "abort", "make_response",
        "Response", "Blueprint", "send_file", "send_from_directory",
        "g", "current_app", "escape", "get_flashed_messages",
    ],
    "sqlite3": [
        "connect", "Connection", "Cursor", "Row", "Error",
        "DatabaseError", "IntegrityError", "OperationalError",
        "ProgrammingError", "NotSupportedError", "InternalError",
        "Warning", "PARSE_DECLTYPES", "PARSE_COLNAMES",
        "sqlite_version", "sqlite_version_info", "register_adapter",
        "register_converter",
    ],
}

# ---- 常用代码模板（中文编程写法，插入后 F5 即可运行） ----
TEMPLATES = {
    "flask": (
        "# Flask 应用骨架 —— 运行后浏览器打开 http://127.0.0.1:5000\n"
        "从 flask 导入 Flask， request， jsonify\n"
        "\n"
        "应用 = Flask（__name__）\n"
        "\n"
        '@应用.route（"/"）\n'
        "定义 首页（）：\n"
        "    返回 \"你好，世界！\"\n"
        "\n"
        '@应用.route（"/你好/<name>"）   # 路由变量名必须用英文\n'
        "定义 问好（name）：\n"
        "    返回 f\"你好，{name}！\"\n"
        "\n"
        '@应用.route（"/api/数据"， methods=["POST"]）\n'
        "定义 接收数据（）：\n"
        "    内容 = request.get_json（）\n"
        "    返回 jsonify（{\"收到\"： 内容}）\n"
        "\n"
        "如果 __name__ == \"__main__\"：\n"
        "    应用.run（host=\"0.0.0.0\"， port=5000， debug=True）   # 改端口改这里；host 删掉则仅本机访问\n"
    ),
    "sqlite": (
        "# SQLite 数据库使用示例\n"
        "导入 sqlite3\n"
        "\n"
        '连接 = sqlite3.connect（"示例.db"）   # 文件不存在会自动创建\n'
        "光标 = 连接.cursor（）\n"
        "\n"
        "# 建表（注意：SQL 语句里的括号、逗号必须用半角）\n"
        '光标.execute（"""CREATE TABLE IF NOT EXISTS 用户(\n'
        "    编号 INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "    名字 TEXT NOT NULL,\n"
        "    年龄 INTEGER\n"
        ')"""）\n'
        "\n"
        "# 插入数据\n"
        '光标.execute（"INSERT INTO 用户(名字, 年龄) VALUES (?, ?)"，\n'
        '              （"小明"， 12））\n'
        "连接.commit（）   # 提交事务\n"
        "\n"
        "# 查询\n"
        '光标.execute（"SELECT * FROM 用户"）\n'
        "对于 行 在 光标.fetchall（）：\n"
        "    输出（行）\n"
        "\n"
        "连接.close（）\n"
    ),
}


class ChineseEditor:
    """主编辑器类"""

    def __init__(self, root):
        self.root = root
        self.file_path = None          # 当前文件完整路径，None 表示尚未保存
        self.current_encoding = "utf-8"  # 当前保存/打开所用编码
        self.font_size = FONT_SIZE
        self._hl_after = None        # 语法高亮防抖定时器句柄
        self._proc = None            # 兼容保留：最近一个运行的子进程（多终端后仅作参考）
        self._tmp_file = None        # 翻译后写入的临时文件
        self._run_queue = None       # 兼容保留：子进程输出队列
        self._terms = []             # 终端会话列表，每个元素：{kind,proc,queue,out,inp,title,done}
        self._term_seq = 0           # 终端序号（给"Python 终端 N"命名）
        self._suggest_win = None     # 导入补全下拉窗口
        self._suggest_listbox = None
        self._suggest_mods = None    # 已安装模块名缓存
        self._suggest_mode = "module"   # 补全模式：module=顶层模块 / member=模块成员
        self._member_cache = None    # 模块成员缓存
        self._just_inserted = False  # 刚通过补全插入模块名（抑制 KeyRelease 重弹）

        # ---- 主题（浅色 / 深色）----
        self._theme_name = "浅色"
        self._theme = THEMES["浅色"]

        # ---- 窗口基本设置 ----
        self.root.title(APP_TITLE)
        self.root.geometry(f"{DEFAULT_SIZE[0]}x{DEFAULT_SIZE[1]}")
        self.root.minsize(*MIN_SIZE)
        self._center_window()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # ---- 界面各区域 ----
        self._create_menubar()
        self._create_toolbar()
        self._create_text_area()
        self._create_statusbar()

        # 绑定全局快捷键
        self._bind_shortcuts()

        # 新建一个空文档作为初始状态
        self.new_file(ask_save=False)

        # 按当前主题上色（浅色默认；深色切换后立即生效）
        self.apply_theme()

    # ==================================================================
    # 界面搭建
    # ==================================================================
    def _center_window(self):
        """让窗口在屏幕中央显示"""
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - DEFAULT_SIZE[0]) // 2
        y = (sh - DEFAULT_SIZE[1]) // 2
        self.root.geometry(f"{DEFAULT_SIZE[0]}x{DEFAULT_SIZE[1]}+{max(x, 0)}+{max(y, 0)}")

    def _create_menubar(self):
        """创建菜单栏：文件 / 编辑 / 查找 / 格式 / 视图 / 帮助"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ---- 文件菜单 ----
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新建(N)", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="打开(O)...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="保存(S)", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="另存为(A)...", accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="退出(X)", accelerator="Alt+F4", command=self.exit_app)
        menubar.add_cascade(label="文件(F)", menu=file_menu)

        # ---- 编辑菜单 ----
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="撤销(U)", accelerator="Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="重做(R)", accelerator="Ctrl+Y", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="剪切(T)", accelerator="Ctrl+X",
                              command=lambda: self.text.event_generate("<<Cut>>"))
        edit_menu.add_command(label="复制(C)", accelerator="Ctrl+C",
                              command=lambda: self.text.event_generate("<<Copy>>"))
        edit_menu.add_command(label="粘贴(P)", accelerator="Ctrl+V",
                              command=lambda: self.text.event_generate("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="全选(A)", accelerator="Ctrl+A", command=self.select_all)
        edit_menu.add_command(label="插入当前日期时间", command=self.insert_datetime)
        menubar.add_cascade(label="编辑(E)", menu=edit_menu)

        # ---- 查找菜单 ----
        find_menu = tk.Menu(menubar, tearoff=0)
        find_menu.add_command(label="查找(F)...", accelerator="Ctrl+F", command=self.open_find_dialog)
        find_menu.add_command(label="查找下一个", accelerator="F3", command=self.find_next)
        find_menu.add_command(label="替换(R)...", accelerator="Ctrl+H", command=self.open_replace_dialog)
        menubar.add_cascade(label="查找", menu=find_menu)

        # ---- 运行菜单（中文编程） ----
        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="运行程序(R)", accelerator="F5", command=self.run_code)
        run_menu.add_command(label="停止运行", command=self.stop_run)
        run_menu.add_separator()
        run_menu.add_command(label="翻译为 Python 预览...", command=self.show_translate_preview)
        menubar.add_cascade(label="运行", menu=run_menu)

        # ---- 模板菜单（常用代码一键插入） ----
        tmpl_menu = tk.Menu(menubar, tearoff=0)
        tmpl_menu.add_command(label="Flask 应用骨架",
                              command=lambda: self.insert_template("flask"))
        tmpl_menu.add_command(label="SQLite 数据库示例",
                              command=lambda: self.insert_template("sqlite"))
        menubar.add_cascade(label="模板", menu=tmpl_menu)

        # ---- 格式菜单（编码选择） ----
        self.encoding_var = tk.StringVar(value="utf-8")
        fmt_menu = tk.Menu(menubar, tearoff=0)
        self.encoding_menu = tk.Menu(fmt_menu, tearoff=0)
        self.encoding_menu.add_radiobutton(label="UTF-8", value="utf-8",
                                           variable=self.encoding_var,
                                           command=lambda: self._switch_encoding("utf-8"))
        self.encoding_menu.add_radiobutton(label="GBK（简体中文）", value="gbk",
                                           variable=self.encoding_var,
                                           command=lambda: self._switch_encoding("gbk"))
        fmt_menu.add_cascade(label="编码", menu=self.encoding_menu)
        menubar.add_cascade(label="格式", menu=fmt_menu)

        # ---- 视图菜单（字号缩放） ----
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="放大字号", accelerator="Ctrl+=", command=self.zoom_in)
        view_menu.add_command(label="缩小字号", accelerator="Ctrl+-", command=self.zoom_out)
        view_menu.add_command(label="恢复默认字号", command=self.zoom_reset)
        # 主题切换子菜单
        theme_menu = tk.Menu(menubar, tearoff=0)
        self._theme_var = tk.StringVar(value=self._theme_name)
        theme_menu.add_radiobutton(label="浅色", variable=self._theme_var, value="浅色",
                                   command=lambda: self.switch_theme("浅色"))
        theme_menu.add_radiobutton(label="深色", variable=self._theme_var, value="深色",
                                   command=lambda: self.switch_theme("深色"))
        view_menu.add_cascade(label="主题", menu=theme_menu)
        menubar.add_cascade(label="视图(V)", menu=view_menu)

        # ---- 帮助菜单 ----
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self.show_about)
        help_menu.add_command(label="联系我们", command=self.show_contact)
        menubar.add_cascade(label="帮助(H)", menu=help_menu)

        # 记录菜单引用，便于主题切换时尝试着色（Windows 原生菜单栏不一定生效）
        self._menubar = menubar
        self._menus = [file_menu, edit_menu, find_menu, run_menu, tmpl_menu,
                       fmt_menu, view_menu, theme_menu, help_menu]

    def _create_toolbar(self):
        """创建工具栏（常用功能的快捷按钮）"""
        bar = ttk.Frame(self.root, padding=(6, 4), style="Toolbar.TFrame")
        bar.pack(side=tk.TOP, fill=tk.X)

        def add_button(text, cmd):
            btn = ttk.Button(bar, text=text, command=cmd, width=6)
            btn.pack(side=tk.LEFT, padx=2)
            return btn

        add_button("新建", self.new_file)
        add_button("打开", self.open_file)
        add_button("保存", self.save_file)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        add_button("撤销", self.undo)
        add_button("重做", self.redo)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        add_button("查找", self.open_find_dialog)
        add_button("替换", self.open_replace_dialog)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        add_button("运行", self.run_code)

    def _create_text_area(self):
        """创建编辑区：行号 + 文本框 + 垂直滚动条"""
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # 垂直滚动条（最右边）
        yscroll = ttk.Scrollbar(main, orient=tk.VERTICAL)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 行号画布（最左边）
        self.line_canvas = tk.Canvas(main, width=LINE_NUM_WIDTH, bg="#f2f2f2",
                                     highlightthickness=0)
        self.line_canvas.pack(side=tk.LEFT, fill=tk.Y)

        # 主文本编辑区（中间）
        # height=1 让请求高度最小：否则 Text 默认请求 24 行的高度，
        # 会把底部终端面板的空间抢光（面板调大也显示不出来）
        self.text = tk.Text(
            main,
            height=1,                       # 请求高度最小，实际由 expand 撑满
            undo=True,                      # 开启撤销/重做
            wrap=tk.WORD,                   # 按单词换行（中文按字换行）
            font=(FONT_FAMILY, FONT_SIZE),
            padx=8, pady=8,
            relief=tk.FLAT,
            yscrollcommand=self._on_text_scroll,
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        yscroll.config(command=self.text.yview)

        # 编辑区变化时刷新行号和状态栏（KeyRelease + Modified 双保险，
        # Modified 覆盖删除、撤销、粘贴、程序性修改等所有内容变化路径）
        self.text.bind("<KeyRelease>", self._on_content_change)
        self.text.bind("<<Modified>>", self._on_content_change)
        # add="+" 追加，避免覆盖上面的状态栏刷新（bind 同一事件默认只保留最后一个）
        self.text.bind("<KeyRelease>", self._maybe_show_suggestions, add="+")
        self.text.bind("<ButtonRelease-1>", self._on_cursor_move)
        self.text.bind("<Configure>", lambda e: self._redraw_line_numbers())
        self.line_canvas.bind("<MouseWheel>", self._on_line_canvas_wheel)

        # 导入补全：点击文本区隐藏列表；列表可见时拦截方向键/Tab/回车/Esc
        self.text.bind("<Button-1>", lambda e: self._hide_suggestions())
        self.text.bind("<Escape>", self._hide_suggestions)
        self.text.bind("<Up>", self._on_suggest_key)
        self.text.bind("<Down>", self._on_suggest_key)
        self.text.bind("<Return>", self._on_suggest_key)
        self.text.bind("<Tab>", self._on_suggest_key)

        self._configure_highlight_tags()
        self._redraw_line_numbers()

    def _create_statusbar(self):
        """创建状态栏：位置 / 字数 / 编码 / 修改标记"""
        self.statusbar = tk.Frame(self.root, bg="#e6e6e6")
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        # 左侧：光标行列位置
        self.pos_label = tk.Label(self.statusbar, text="行 1，列 1",
                                  bg="#e6e6e6", anchor="w", padx=8)
        self.pos_label.pack(side=tk.LEFT)

        # 右侧：字数、编码、修改标记
        self.count_label = tk.Label(self.statusbar, text="字数 0 | 汉字 0 | 行数 1",
                                    bg="#e6e6e6", anchor="e", padx=8)
        self.count_label.pack(side=tk.RIGHT)

        self.enc_label = tk.Label(self.statusbar, text="UTF-8",
                                  bg="#e6e6e6", anchor="e", padx=4)
        self.enc_label.pack(side=tk.RIGHT)

        self.mod_label = tk.Label(self.statusbar, text="", bg="#e6e6e6",
                                  fg="#c0392b", anchor="e", padx=8)
        self.mod_label.pack(side=tk.RIGHT)

    def _bind_shortcuts(self):
        """绑定全局快捷键"""
        self.root.bind_all("<Control-n>", lambda e: self.new_file())
        self.root.bind_all("<Control-o>", lambda e: self.open_file())
        self.root.bind_all("<Control-s>", lambda e: self.save_file())
        self.root.bind_all("<Control-Shift-S>", lambda e: self.save_as())
        self.root.bind_all("<Control-f>", lambda e: self.open_find_dialog())
        self.root.bind_all("<Control-h>", lambda e: self.open_replace_dialog())
        self.root.bind_all("<F3>", lambda e: self.find_next())
        self.root.bind_all("<Control-a>", lambda e: self.select_all())
        self.root.bind_all("<Control-z>", lambda e: self.undo())
        self.root.bind_all("<Control-y>", lambda e: self.redo())
        self.root.bind_all("<Control-equal>", lambda e: self.zoom_in())
        self.root.bind_all("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind_all("<Control-Key-0>", lambda e: self.zoom_reset())
        self.root.bind_all("<F5>", lambda e: self.run_code())

    # ==================================================================
    # 文件操作
    # ==================================================================
    def new_file(self, ask_save=True):
        """新建文件"""
        if ask_save and not self._confirm_discard():
            return
        self.text.delete("1.0", tk.END)
        self.file_path = None
        self.root.title(APP_TITLE + " - 未命名")
        self.text.edit_reset()          # 清空撤销历史
        self.text.edit_modified(False)
        self._on_content_change()

    def _open_path(self, path):
        """按路径直接打开文件（供双击 .cnpy / 命令行参数调用）"""
        if not self._confirm_discard():
            return
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            messagebox.showerror("打开失败", f"无法读取文件：\n{e}")
            return

        # 尝试用不同编码解码，优先 UTF-8
        content = None
        used_enc = None
        for enc in ENCODINGS:
            try:
                content = raw.decode(enc)
                used_enc = enc
                break
            except UnicodeDecodeError:
                continue
        if content is None:
            # 都失败则用 UTF-8 宽容解码，不丢失内容
            content = raw.decode("utf-8", errors="replace")
            used_enc = "utf-8"
            messagebox.showwarning("编码提示", "无法完全识别文件编码，已按 UTF-8 打开。")

        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.file_path = path
        self.current_encoding = used_enc
        self.encoding_var.set(used_enc)
        self.root.title(f"{os.path.basename(path)} - {APP_TITLE}")
        self.text.edit_reset()
        self.text.edit_modified(False)
        self._on_content_change()

    def open_file(self):
        """打开文件（自动识别编码）"""
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="打开文件",
            filetypes=[
                ("中文编程文件", "*.cnpy"),
                ("Python 文件", "*.py"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*"),
            ],
        )
        if not path:
            return
        self._open_path(path)

    def save_file(self):
        """保存；没有文件名则走另存为"""
        if not self.file_path:
            return self.save_as()
        self._write_to_disk(self.file_path)
        self.root.title(f"{os.path.basename(self.file_path)} - {APP_TITLE}")
        self.text.edit_modified(False)
        self._on_content_change()
        return True

    def save_as(self):
        """另存为"""
        path = filedialog.asksaveasfilename(
            title="另存为",
            defaultextension=".cnpy",
            filetypes=[
                ("中文编程文件", "*.cnpy"),
                ("Python 文件", "*.py"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*"),
            ],
        )
        if not path:
            return False
        self.file_path = path
        ok = self.save_file()
        return ok

    def _write_to_disk(self, path):
        """按当前选择的编码写入文件"""
        content = self.text.get("1.0", "end-1c")
        try:
            data = content.encode(self.current_encoding)
        except UnicodeEncodeError:
            # 内容里有当前编码无法表示的字符（例如 GBK 外的生僻字）时自动退回 UTF-8
            messagebox.showwarning(
                "编码提示",
                f"内容包含无法用 {self.current_encoding.upper()} 表示的字符，已改用 UTF-8 保存。",
            )
            self.current_encoding = "utf-8"
            self.encoding_var.set("utf-8")
            data = content.encode("utf-8")
        with open(path, "wb") as f:
            f.write(data)

    def _confirm_discard(self):
        """内容有修改时，询问是否保存/放弃；返回 True 表示可以继续"""
        if not self.text.edit_modified():
            return True
        answer = messagebox.askyesnocancel(
            "未保存的修改",
            "当前内容尚未保存，是否保存？\n"
            "是=保存   否=不保存   取消=返回",
        )
        if answer is None:       # 取消
            return False
        if answer:               # 是 -> 保存
            return self.save_file()
        return True              # 否 -> 放弃修改

    def exit_app(self):
        """退出程序"""
        if self._confirm_discard():
            self.root.destroy()

    # ==================================================================
    # 编辑操作
    # ==================================================================
    def undo(self):
        try:
            self.text.edit_undo()
        except tk.TclError:
            pass  # 没有可撤销的内容

    def redo(self):
        try:
            self.text.edit_redo()
        except tk.TclError:
            pass

    def select_all(self):
        self.text.tag_add("sel", "1.0", "end-1c")
        return "break"

    def insert_datetime(self):
        """在光标处插入当前日期时间"""
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.text.insert(tk.INSERT, now)

    def zoom_in(self):
        self._set_font_size(self.font_size + 1)

    def zoom_out(self):
        self._set_font_size(max(self.font_size - 1, 8))

    def zoom_reset(self):
        self._set_font_size(FONT_SIZE)

    def _set_font_size(self, size):
        self.font_size = size
        self.text.config(font=(FONT_FAMILY, size))
        self._redraw_line_numbers()

    # ==================================================================
    # 查找 / 替换
    # ==================================================================
    def _search_content(self):
        """返回当前要查找的关键词（来自查找对话框）"""
        if hasattr(self, "find_var"):
            return self.find_var.get()
        return ""

    def find_next(self):
        """从光标位置向后查找，找到末尾后循环回开头"""
        keyword = self._search_content()
        if not keyword:
            self.open_find_dialog()
            return False

        start = self.text.index(tk.INSERT)
        pos = self.text.search(keyword, start, stopindex=tk.END, nocase=False)
        if not pos:
            # 从头再找一遍（循环查找）
            pos = self.text.search(keyword, "1.0", stopindex=start, nocase=False)
        if pos:
            end = self.text.index(f"{pos}+{len(keyword)}c")
            self.text.tag_remove("sel", "1.0", tk.END)
            self.text.tag_add("sel", pos, end)
            self.text.mark_set(tk.INSERT, end)
            self.text.see(pos)
            return True
        messagebox.showinfo("查找", f"未找到：{keyword}")
        return False

    def open_find_dialog(self):
        """打开查找对话框"""
        self._ensure_dialogs()
        self.find_dialog.deiconify()
        self.find_dialog.lift()
        self.find_entry.focus_set()
        self.find_entry.select_range(0, tk.END)

    def open_replace_dialog(self):
        """打开替换对话框"""
        self.open_find_dialog()
        self.replace_dialog.deiconify()
        self.replace_dialog.lift()

    def _ensure_dialogs(self):
        """按需创建查找/替换对话框（避免一启动就全建出来）"""
        if not hasattr(self, "find_dialog"):
            self._build_find_dialog()
        if not hasattr(self, "replace_dialog"):
            self._build_replace_dialog()

    def _build_find_dialog(self):
        self.find_dialog = tk.Toplevel(self.root)
        self.find_dialog.title("查找")
        self.find_dialog.resizable(False, False)
        self.find_var = tk.StringVar()

        frm = ttk.Frame(self.find_dialog, padding=10)
        frm.pack()
        ttk.Label(frm, text="查找内容：").grid(row=0, column=0, sticky="w")
        self.find_entry = ttk.Entry(frm, textvariable=self.find_var, width=28)
        self.find_entry.grid(row=0, column=1, padx=6, pady=4)
        self.find_entry.bind("<Return>", lambda e: self.find_next())

        ttk.Button(frm, text="查找下一个", width=12, command=self.find_next)\
            .grid(row=0, column=2, padx=4)
        ttk.Button(frm, text="关闭", width=8,
                   command=lambda: self.find_dialog.withdraw())\
            .grid(row=1, column=2, sticky="e", pady=(6, 0))

        # 关闭时只隐藏，不销毁（保留上次输入）
        self.find_dialog.protocol("WM_DELETE_WINDOW", self.find_dialog.withdraw)

    def _build_replace_dialog(self):
        self.replace_dialog = tk.Toplevel(self.root)
        self.replace_dialog.title("替换")
        self.replace_dialog.resizable(False, False)
        self.replace_var = tk.StringVar()

        frm = ttk.Frame(self.replace_dialog, padding=10)
        frm.pack()
        ttk.Label(frm, text="查找内容：").grid(row=0, column=0, sticky="w")
        self.replace_entry = ttk.Entry(frm, textvariable=self.replace_var, width=28)
        self.replace_entry.grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(frm, text="替换为：").grid(row=1, column=0, sticky="w")
        self.repl_to_entry = ttk.Entry(frm, width=28)
        self.repl_to_entry.grid(row=1, column=1, padx=6, pady=4)

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=3, sticky="e", pady=(8, 0))
        ttk.Button(btns, text="替换", width=8,
                   command=self._replace_once).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="全部替换", width=10,
                   command=self._replace_all).pack(side=tk.LEFT, padx=3)
        ttk.Button(btns, text="关闭", width=8,
                   command=lambda: self.replace_dialog.withdraw()).pack(side=tk.LEFT, padx=3)

        self.replace_dialog.protocol("WM_DELETE_WINDOW", self.replace_dialog.withdraw)

    def _replace_once(self):
        """替换当前选中的匹配；若没有选中则先查找"""
        keyword = self.replace_var.get()
        if not keyword:
            messagebox.showwarning("替换", "请先输入要查找的内容。")
            return
        # 把替换对话框的关键词同步到查找框
        self.find_var.set(keyword)

        sel = self.text.tag_ranges("sel")
        if sel:
            selected = self.text.get(sel[0], sel[1])
            if selected == keyword:
                self.text.delete(sel[0], sel[1])
                self.text.insert(sel[0], self.repl_to_entry.get())
                self._on_content_change()
        self.find_next()

    def _replace_all(self):
        """全部替换并统计数量"""
        keyword = self.replace_var.get()
        if not keyword:
            messagebox.showwarning("替换", "请先输入要查找的内容。")
            return
        content = self.text.get("1.0", "end-1c")
        count = content.count(keyword)
        if count == 0:
            messagebox.showinfo("替换", "未找到要替换的内容。")
            return
        self.find_var.set(keyword)
        new_content = content.replace(keyword, self.repl_to_entry.get())
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", new_content)
        self._on_content_change()
        messagebox.showinfo("替换", f"已替换 {count} 处。")

    # ==================================================================
    # 状态栏 / 行号
    # ==================================================================
    def _on_content_change(self, event=None):
        """内容变化：刷新行号、字数、修改标记、标题星号，并触发语法高亮"""
        self._redraw_line_numbers()
        self._update_status()
        self._update_title_mark()
        self._highlight()

    def _on_cursor_move(self, event=None):
        """光标移动：刷新行列位置"""
        self._update_cursor_pos()

    def _on_text_scroll(self, first, last):
        """主文本滚动时同步行号画布和滚动条"""
        self.line_canvas.yview_moveto(float(first))

    def _on_line_canvas_wheel(self, event):
        """鼠标在行号区域滚动时，让主文本也跟着滚动"""
        self.text.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _redraw_line_numbers(self):
        """重新绘制左侧行号"""
        self.line_canvas.delete("all")
        # 根据文本总行数动态调整行号区域宽度
        total_lines = int(self.text.index("end-1c").split(".")[0])
        width = max(LINE_NUM_WIDTH, 18 + len(str(total_lines)) * 10)
        if self.line_canvas.winfo_width() != width:
            self.line_canvas.config(width=width)

        i = self.text.index("@0,0")          # 当前可见的第一行
        while True:
            dline = self.text.dlineinfo(i)   # 该行在画布上的几何信息
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.line_canvas.create_text(
                width - 12, y, anchor="ne",
                text=linenum, fill=self._theme["line_fg"],
                font=(FONT_FAMILY, max(self.font_size - 2, 8)),
            )
            i = self.text.index(f"{i}+1line")

    # ----------------------------------------------------------------
    # 主题切换（浅色 / 深色）
    # ----------------------------------------------------------------
    def switch_theme(self, name):
        """切换主题并立即应用"""
        self._theme_name = name
        self._theme = THEMES[name]
        self._theme_var.set(name)
        self.apply_theme()

    def apply_theme(self):
        """把当前主题的颜色应用到界面各区域（含 ttk 按钮/标签页/滚动条）"""
        th = self._theme
        dark = self._theme_name == "深色"
        try:
            # ttk 样式（clam 主题支持自定义颜色，让按钮/标签页/滚动条一起变深）
            if not hasattr(self, "_style"):
                self._style = ttk.Style(self.root)
                try:
                    self._style.theme_use("clam")
                except Exception:
                    pass
            if dark:
                sbg, sfg = th["status_bg"], th["status_fg"]
                act = "#3c3c3c"
            else:
                sbg, sfg = "#f0f0f0", "#1a1a1a"
                act = "#dcdcdc"
            s = self._style
            s.configure("TButton", background=sbg, foreground=sfg,
                        bordercolor=th["line_bg"])
            s.map("TButton",
                  background=[("active", act)],
                  foreground=[("active", "#ffffff" if dark else "#000000")])
            s.configure("TMenubutton", background=sbg, foreground=sfg,
                        bordercolor=th["line_bg"])
            s.map("TMenubutton", background=[("active", act)],
                  foreground=[("active", "#ffffff" if dark else "#000000")])
            s.configure("Toolbar.TFrame", background=sbg)
            s.configure("TNotebook", background=th["root_bg"],
                        bordercolor=th["line_bg"])
            s.configure("TNotebook.Tab", background=th["line_bg"], foreground=sfg,
                        bordercolor=th["line_bg"])
            s.map("TNotebook.Tab",
                  background=[("selected", th["status_bg"])],
                  foreground=[("selected", "#ffffff" if dark else "#000000")])
            s.configure("Vertical.TScrollbar", background=th["line_bg"],
                        bordercolor=th["line_bg"], troughcolor=th["root_bg"],
                        arrowcolor=sfg)
            s.configure("Horizontal.TScrollbar", background=th["line_bg"],
                        bordercolor=th["line_bg"], troughcolor=th["root_bg"],
                        arrowcolor=sfg)
            s.configure("TSeparator", background=th["line_bg"])

            # 主窗口与内容区
            self.root.configure(bg=th["root_bg"])
            # 编辑区
            self.text.config(bg=th["editor_bg"], fg=th["editor_fg"],
                             insertbackground=th["editor_fg"])
            # 行号画布
            self.line_canvas.config(bg=th["line_bg"])
            # 状态栏
            self.statusbar.config(bg=th["status_bg"])
            for w in (self.pos_label, self.count_label, self.enc_label, self.mod_label):
                w.config(bg=th["status_bg"], fg=th["status_fg"])
            # 语法高亮 tag 颜色（已标记的文本会自动跟着变色）
            for tag, color in th["hl"].items():
                self.text.tag_configure(tag, foreground=color)
            self.text.tag_lower("hl_comment")
            # 菜单下拉项着色（菜单栏本身是 Windows 原生绘制，改不了；下拉项可以）
            for m in getattr(self, "_menus", []):
                try:
                    m.config(bg=th["status_bg"], fg=sfg,
                             activebackground=act,
                             activeforeground="#ffffff" if dark else "#000000",
                             bd=0, relief="flat")
                except Exception:
                    pass
            # 行号文字颜色变了，重绘一次
            self._redraw_line_numbers()
        except Exception:
            pass

    def _update_status(self):
        """更新字数统计与编码显示"""
        content = self.text.get("1.0", "end-1c")
        total = len(content)
        chinese = sum(1 for ch in content if "\u4e00" <= ch <= "\u9fff")
        lines = int(self.text.index("end-1c").split(".")[0])
        self.count_label.config(text=f"字数 {total} | 汉字 {chinese} | 行数 {lines}")
        self.enc_label.config(text=self.current_encoding.upper())
        self._update_cursor_pos()
        self._update_title_mark()

    def _update_cursor_pos(self):
        """更新光标行列位置"""
        index = self.text.index(tk.INSERT)
        row, col = index.split(".")
        self.pos_label.config(text=f"行 {row}，列 {int(col) + 1}")

    def _update_title_mark(self):
        """标题栏和状态栏显示修改状态"""
        modified = self.text.edit_modified()
        self.mod_label.config(text="已修改" if modified else "")
        title = self.root.title()
        if modified and not title.startswith("*"):
            self.root.title("*" + title)
        elif not modified and title.startswith("*"):
            self.root.title(title[1:])

    def _switch_encoding(self, enc):
        """手动切换保存编码"""
        self.current_encoding = enc
        self.enc_label.config(text=enc.upper())

    # ==================================================================
    # Python 语法高亮
    # ==================================================================
    def _configure_highlight_tags(self):
        """配置高亮配色。只设置颜色、不设置字体，避免与字号缩放冲突。"""
        for tag, color in self._theme["hl"].items():
            self.text.tag_configure(tag, foreground=color)
        # 让字符串的优先级高于注释：字符串里的 # 保持绿色，不会被误标成注释
        self.text.tag_lower("hl_comment")

    def _highlight(self, event=None):
        """内容变化后延迟执行高亮（100ms 防抖，连续打字不卡顿）"""
        if self._hl_after:
            self.root.after_cancel(self._hl_after)
        self._hl_after = self.root.after(100, self._apply_highlight)

    def _apply_highlight(self):
        """真正执行高亮：先精确扫描字符串/注释，再对代码区着色"""
        self._hl_after = None
        text = self.text
        for tag in self._theme["hl"]:
            text.tag_remove(tag, "1.0", tk.END)

        content = text.get("1.0", "end-1c")
        if not content:
            return

        # 1) 状态机扫描：找出字符串与注释的区间（互不重叠，字符串内的#不算注释）
        str_ranges, cmt_ranges = self._scan_regions(content)

        # 2) 给字符串和注释上色
        for start, end in str_ranges:
            text.tag_add("hl_string", f"1.0+{start}c", f"1.0+{end}c")
        for start, end in cmt_ranges:
            text.tag_add("hl_comment", f"1.0+{start}c", f"1.0+{end}c")

        # 3) 把字符串/注释区域替换成空格（保留换行），
        #    这样关键词正则不会误命中注释里的 print、字符串里的关键字等
        chars = list(content)
        for start, end in str_ranges + cmt_ranges:
            for i in range(start, end):
                if chars[i] != "\n":
                    chars[i] = " "
        masked = "".join(chars)

        # 4) 对代码区做单词类着色（每个正则的 group(1) 就是要着色的区间）
        kw = "|".join(HL_KEYWORDS)
        bi = "|".join(HL_BUILTINS)
        patterns = (
            (rf"\b({kw})\b", "hl_kw"),
            (rf"\b({bi})\b", "hl_builtin"),
            (r"(\b\d+(?:\.\d+)?\b)", "hl_number"),
            (r"\b(?:def|class)\s+([^\W\d]\w*)", "hl_funcname"),  # 支持中文函数名
        )
        for regex, tag in patterns:
            for m in re.finditer(regex, masked):
                text.tag_add(tag, f"1.0+{m.start(1)}c", f"1.0+{m.end(1)}c")

    @staticmethod
    def _scan_regions(content):
        """逐字符扫描，返回 (字符串区间列表, 注释区间列表)，二者互不重叠"""
        str_ranges, cmt_ranges = [], []
        i, n = 0, len(content)
        while i < n:
            ch = content[i]
            if ch == "#":
                # 注释：从 # 到行尾
                j = content.find("\n", i)
                if j == -1:
                    j = n
                cmt_ranges.append((i, j))
                i = j
            elif ch in "\"'":
                quote = ch
                if content[i:i + 3] == quote * 3:
                    # 三引号字符串：找下一个三引号
                    j = content.find(quote * 3, i + 3)
                    j = n if j == -1 else j + 3
                else:
                    # 普通字符串：处理反斜杠转义
                    j = i + 1
                    while j < n:
                        if content[j] == "\\":
                            j += 2
                            continue
                        if content[j] == quote:
                            j += 1
                            break
                        j += 1
                str_ranges.append((i, j))
                i = j
            else:
                i += 1
        return str_ranges, cmt_ranges

    # ==================================================================
    # 导入自动补全
    # ==================================================================
    def _maybe_show_suggestions(self, event=None):
        """检测光标前是否在写导入语句，弹出模块或成员补全列表"""
        if self._just_inserted:
            self._just_inserted = False   # 刚插入模块名，这轮不再弹
            return
        if self._suggest_win is not None and self._suggest_win.winfo_viewable():
            if event and event.keysym in ("Return", "Tab", "Up", "Down"):
                return  # 这些键由 _on_suggest_key 专门处理
        line = self.text.get("insert linestart", "insert")

        # 模式一：从 X 导入 <成员>（from X import <member>）
        m = re.search(
            r"(?:从\s+([A-Za-z0-9_.]+)\s+导入|from\s+([A-Za-z0-9_.]+)\s+import)"
            r"\s+([A-Za-z0-9_,， ]*)$",
            line,
        )
        if m:
            modname = m.group(1) or m.group(2)
            tail = m.group(3)
            # 按逗号/空格切分，兼容全角逗号
            prefix = re.split(r"[,\s，]+", tail)[-1] if tail.strip() else ""
            names = self._get_members(modname)
            pl = prefix.lower()
            matched = [n for n in names if n.lower().startswith(pl)] if prefix else names
            matched = matched[:50]
            if matched:
                self._show_suggestions(matched, mode="member")
            else:
                self._hide_suggestions()
            return

        # 模式二：导入 <模块>（import <module>）
        m = re.search(r"(?:导入|import)\s+([A-Za-z0-9_.]*)$", line)
        if not m:
            self._hide_suggestions()
            return
        prefix = m.group(1)
        mods = self._get_modules()
        if not mods:
            return
        pl = prefix.lower()
        matched = [n for n in mods if n.lower().startswith(pl)] if prefix else mods
        matched = matched[:50]   # 只显示前 50 个，避免列表过长
        if not matched:
            self._hide_suggestions()
            return
        self._show_suggestions(matched)

    def _get_modules(self):
        """列出当前 Python 环境可导入的模块（首次获取后缓存）。
        包括：文件系统上的模块（pkgutil）+ 编译进解释器的内置模块（math、sys 等）。
        常用模块排在前面，方便学习时直接看到。
        """
        if self._suggest_mods is None:
            common = ("sys os math re json random time datetime tkinter "
                      "collections itertools functools pathlib string urllib "
                      "requests numpy pandas matplotlib PIL sqlite3 csv "
                      "hashlib base64 threading queue subprocess").split()
            try:
                import pkgutil
                names = {m.name for m in pkgutil.iter_modules()}
                names.update(sys.builtin_module_names)
                self._suggest_mods = (
                    [c for c in common if c in names]
                    + sorted(names - set(common))
                )
            except Exception:
                self._suggest_mods = []
        return self._suggest_mods

    def _get_members(self, modname):
        """列出模块内可供导入的成员（动态导入成功则用 dir()，失败用兜底表）。
        结果按名称排序并缓存。
        """
        if self._member_cache is None:
            self._member_cache = {}
        if modname in self._member_cache:
            return self._member_cache[modname]
        names = PRESET_MEMBERS.get(modname, [])
        try:
            mod = __import__(modname)
            dyn = sorted(n for n in dir(mod) if not n.startswith("_"))
            if dyn:
                names = dyn
        except Exception:
            pass   # 导入失败就用兜底表
        self._member_cache[modname] = names
        return names

    def _create_suggest_win(self):
        """创建无边框置顶的下拉列表窗口"""
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)          # 去掉标题栏边框
        win.attributes("-topmost", True)    # 始终置顶
        box = tk.Listbox(win, height=8, activestyle="dot",
                         font=(FONT_FAMILY, 12), exportselection=False,
                         highlightthickness=1, highlightbackground="#c8c8c8")
        box.pack()
        box.bind("<ButtonRelease-1>", lambda e: self._insert_suggestion())
        win.bind("<Escape>", self._hide_suggestions)
        self._suggest_win = win
        self._suggest_listbox = box

    def _show_suggestions(self, matched, mode="module"):
        if self._suggest_win is None:
            self._create_suggest_win()
        self._suggest_mode = mode
        box = self._suggest_listbox
        box.delete(0, tk.END)
        for name in matched:
            box.insert(tk.END, name)
        box.selection_clear(0, tk.END)
        box.selection_set(0)
        # 让列表显示在光标所在行正下方
        dline = self.text.dlineinfo("insert")
        if dline:
            bx, by = dline[0], dline[1]
            bh = dline[3] if len(dline) > 3 else 20
            x = self.text.winfo_rootx() + bx
            y = self.text.winfo_rooty() + by + bh + 2
            self._suggest_win.geometry(f"+{x}+{y}")
        self._suggest_win.deiconify()
        self._suggest_win.lift()

    def _hide_suggestions(self, event=None):
        if self._suggest_win is not None:
            self._suggest_win.withdraw()

    def _insert_suggestion(self):
        """把选中的模块名/成员名插入光标处（替换掉已输入的前缀）"""
        if self._suggest_win is None or not self._suggest_win.winfo_viewable():
            return
        sel = self._suggest_listbox.curselection()
        if not sel:
            return
        mod_name = self._suggest_listbox.get(sel[0])
        line = self.text.get("insert linestart", "insert")
        if self._suggest_mode == "member":
            # 从 X 导入 <成员>：只替换最后一个片段（逗号后的部分）
            m = re.search(
                r"(?:从\s+[A-Za-z0-9_.]+\s+导入|from\s+[A-Za-z0-9_.]+\s+import)"
                r"\s+([A-Za-z0-9_,， ]*)$",
                line,
            )
            if m and m.group(1).strip():
                # 按逗号/空格切分，兼容全角逗号
                prefix = re.split(r"[,\s，]+", m.group(1))[-1]
                if prefix:
                    self.text.delete(f"insert-{len(prefix)}c", "insert")
        else:
            # 导入 <模块>：替换已输入的模块名前缀
            m = re.search(r"(?:导入|import)\s+([A-Za-z0-9_.]*)$", line)
            if m and m.group(1):
                self.text.delete(f"insert-{len(m.group(1))}c", "insert")
        self.text.insert("insert", mod_name)
        self._hide_suggestions()
        self._just_inserted = True
        self.text.focus_set()

    def _on_suggest_key(self, event):
        """列表可见时：上下选择、Tab/Enter 确认、否则走默认行为"""
        if self._suggest_win is None or not self._suggest_win.winfo_viewable():
            return None
        box = self._suggest_listbox
        if event.keysym == "Down":
            sel = box.curselection()
            idx = (sel[0] + 1) if sel else 0
            if idx < box.size():
                box.selection_clear(0, tk.END)
                box.selection_set(idx)
                box.see(idx)
            return "break"
        if event.keysym == "Up":
            sel = box.curselection()
            idx = (sel[0] - 1) if sel else 0
            if idx >= 0:
                box.selection_clear(0, tk.END)
                box.selection_set(idx)
                box.see(idx)
            return "break"
        if event.keysym in ("Return", "Tab"):
            self._insert_suggestion()
            return "break"
        return None

    def insert_template(self, key):
        """在光标处插入常用代码模板"""
        code = TEMPLATES.get(key)
        if not code:
            return
        # 光标前有缩进则按缩进对齐插入（保持已有缩进的代码风格）
        line = self.text.get("insert linestart", "insert")
        indent = re.match(r"^[\t ]*", line).group(0)
        if indent and code.strip():
            code = "\n".join(
                (indent + ln) if ln.strip() else ln for ln in code.splitlines()
            ) + "\n"
        self.text.insert("insert", code)
        self._on_content_change()

    # ==================================================================
    # 中文编程：翻译 + 运行
    # ==================================================================
    def translate_to_python(self, code):
        """把中文代码翻译成标准 Python。
        只翻译代码区；字符串和注释里的中文原样保留。
        """
        str_ranges, cmt_ranges = self._scan_regions(code)
        literals = sorted(str_ranges + cmt_ranges)

        parts = []
        pos = 0
        for s, e in literals:
            parts.append(self._translate_code(code[pos:s]))   # 代码段：翻译
            parts.append(code[s:e])                            # 字符串/注释：保留
            pos = e
        parts.append(self._translate_code(code[pos:]))
        return "".join(parts)

    @staticmethod
    def _translate_code(seg):
        """翻译一段纯代码：全角标点转半角 + 中文词表替换"""
        seg = seg.translate(PUNCT_TRANS)
        # 中文词前后不能是汉字/字母/数字/下划线，避免"打印机"里的"打印"被误替换
        for zh, en in CN_MAPPING_SORTED:
            seg = re.sub(
                rf"(?<![A-Za-z0-9_\u4e00-\u9fff]){re.escape(zh)}(?![A-Za-z0-9_\u4e00-\u9fff])",
                en, seg,
            )
        return seg

    # ----------------------------------------------------------------
    # 运行
    # ----------------------------------------------------------------
    def _python_exe(self):
        """返回用于运行用户代码的 Python 解释器路径。

        直接跑 .py 时就是当前解释器（sys.executable）；
        打包成 exe 后 sys.executable 指向编辑器自身，必须另找系统的 python.exe。
        """
        if not getattr(sys, "frozen", False):
            return sys.executable
        # 打包成 exe 的情况：按优先级找系统 Python
        candidates = [
            os.environ.get("CN_EDITOR_PYTHON"),   # 允许用户自定义
            shutil.which("python"),
            shutil.which("python3"),
            r"E:\python3.13\python.exe",
        ]
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        return "python"   # 兜底：交给 PATH，找不到时子进程会报错

    def run_code(self):
        """翻译当前代码并用真实 Python 运行：每次 F5 新开一个终端标签（可多开）"""
        code = self.text.get("1.0", "end-1c")
        if not code.strip():
            return
        title = os.path.basename(self.file_path) if self.file_path else "未命名"
        self._start_run_term(title, code)

    def _start_run_term(self, title, code):
        """创建运行终端：翻译 → 写临时文件 → 子进程运行"""
        # 自动清理"已结束"的旧运行标签，避免标签栏被堆爆（REPL/CMD 手动开的保留）
        for t in list(self._terms):
            if t["kind"] == "run" and t["done"]:
                try:
                    self._close_term(t)
                except Exception:
                    pass
        py_code = self.translate_to_python(code)
        self._ensure_term_panel()
        term = self._new_term_page(title)

        self._append_term(term, "正在运行（已自动翻译为 Python）...\n")

        fd, tmp = tempfile.mkstemp(suffix=".py", prefix="cn_editor_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(py_code)
        term["tmp_file"] = tmp

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            term["proc"] = subprocess.Popen(
                [self._python_exe(), "-u", tmp],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", env=env,
                # 运行目录跟随当前文件所在目录：脚本里的相对路径资源（数据库、文件）
                # 按用户直觉与源文件同目录，而不是临时目录
                cwd=os.path.dirname(os.path.abspath(self.file_path)) if self.file_path else None,
            )
        except OSError as e:
            self._append_term(term, f"启动失败：{e}\n", "err")
            term["done"] = True
            return
        self._proc = term["proc"]
        self._run_queue = term["queue"]

        threading.Thread(target=self._read_stream,
                         args=(term["proc"].stdout, "out", term["queue"]), daemon=True).start()
        threading.Thread(target=self._read_stream,
                         args=(term["proc"].stderr, "err", term["queue"]), daemon=True).start()
        self.root.after(100, lambda: self._poll_term(term))

    def _start_repl_term(self, title=None):
        """新开一个交互式 Python 终端（像 VSCode 的 + 新终端），输入中文也会自动翻译"""
        self._term_seq += 1
        if title is None:
            title = f"Python 终端 {self._term_seq}"
        self._ensure_term_panel()
        term = self._new_term_page(title)
        term["kind"] = "repl"

        # 自写 REPL 引导：保持会话状态，自己打印 >>> 提示符（Windows 管道模式没有 tty）
        boot = (
            "import sys, code\n"
            "c = code.InteractiveConsole()\n"
            "sys.stdout.write('>>> '); sys.stdout.flush()\n"
            "buf = []\n"
            "while True:\n"
            "    line = sys.stdin.readline()\n"
            "    if not line:\n"
            "        break\n"
            "    buf.append(line)\n"
            "    more = c.push(''.join(buf))\n"
            "    if more:\n"
            "        sys.stdout.write('... '); sys.stdout.flush()\n"
            "        continue\n"
            "    buf.clear()\n"
            "    sys.stdout.write('>>> '); sys.stdout.flush()\n"
        )
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            term["proc"] = subprocess.Popen(
                [self._python_exe(), "-u", "-c", boot],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", env=env,
                cwd=os.path.dirname(os.path.abspath(self.file_path)) if self.file_path else None,
            )
        except OSError as e:
            self._append_term(term, f"启动失败：{e}\n", "err")
            term["done"] = True
            return
        self._proc = term["proc"]
        self._run_queue = term["queue"]
        threading.Thread(target=self._read_stream,
                         args=(term["proc"].stdout, "out", term["queue"]), daemon=True).start()
        threading.Thread(target=self._read_stream,
                         args=(term["proc"].stderr, "err", term["queue"]), daemon=True).start()
        self.root.after(100, lambda: self._poll_term(term))

    def _start_shell_term(self, shell="cmd"):
        """新开一个系统 Shell 终端（cmd 或 PowerShell）。

        · cmd：真实逐行交互（管道 stdin 每行即命令），先自动 chcp 65001 切 UTF-8；
        · powershell：powershell.exe 管道模式是"读完才执行"无法逐行交互，
          改为每条命令开一个 -Command 子进程执行（输出正常，变量不保留）。
        """
        names = {"cmd": "CMD", "powershell": "PowerShell"}
        self._term_seq += 1
        title = f"{names.get(shell, shell)} 终端 {self._term_seq}"
        self._ensure_term_panel()
        term = self._new_term_page(title)
        term["kind"] = "shell"
        term["shell"] = shell

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        if shell == "cmd":
            argv = [os.environ.get("COMSPEC", "cmd.exe")]
        else:
            # PowerShell：启动时就把控制台输出切到 UTF-8，
            # 否则提示符里的中文路径会用 GBK 输出 → 解码成乱码
            argv = [
                "powershell.exe", "-NoLogo", "-NoExit", "-Command",
                "$([Console]::OutputEncoding=[System.Text.Encoding]::UTF8)",
            ]
        try:
            term["proc"] = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", env=env,
                cwd=os.path.dirname(os.path.abspath(self.file_path)) if self.file_path else None,
            )
        except OSError as e:
            self._append_term(term, f"启动失败：{e}\n", "err")
            term["done"] = True
            return
        self._proc = term["proc"]
        self._run_queue = term["queue"]
        # cmd 走管道逐行交互：先切 UTF-8 代码页，再清屏——
        # 把切换前用 GBK 输出的启动横幅/第一个提示符（乱码）清掉
        if shell == "cmd":
            try:
                term["proc"].stdin.write("chcp 65001>nul\ncls\n")
                term["proc"].stdin.flush()
            except OSError:
                pass
        self._append_term(term, f"# {title} 已就绪\n")
        threading.Thread(target=self._read_stream,
                         args=(term["proc"].stdout, "out", term["queue"], "utf-8"), daemon=True).start()
        threading.Thread(target=self._read_stream,
                         args=(term["proc"].stderr, "err", term["queue"], "utf-8"), daemon=True).start()
        self.root.after(100, lambda: self._poll_term(term))

    def _run_ps_command(self, term, text):
        """PowerShell 终端：每条命令起一个子进程执行（无状态，输出正确）"""
        cmd = "$([Console]::OutputEncoding=[System.Text.Encoding]::UTF8);" + text
        try:
            p = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=os.path.dirname(os.path.abspath(self.file_path)) if self.file_path else None,
                timeout=600,
            )
        except Exception as e:
            self._append_term(term, f"[执行失败：{e}]\n", "err")
            return
        if p.stdout:
            self._append_term(term, p.stdout)
        if p.stderr:
            self._append_term(term, p.stderr, "err")

    def _read_stream(self, stream, tag, queue, enc="utf-8"):
        """后台线程：持续读取子进程输出（每个终端自己的队列）。

        关键点：
        · 用二进制层 read1() 按可用块读取（不等待换行），
          这样 input() 的提示词（没有换行结尾）也能实时显示；
        · 用增量解码器处理 UTF-8，避免多字节字符被切半；
        · 只有真正读到 EOF 才关闭管道，绝不提前关——
          提前关闭会让子进程写输出时 BrokenPipe 崩溃。
        """
        decoder = codecs.getincrementaldecoder(enc)("replace")
        eof = False
        try:
            while True:
                chunk = stream.buffer.read1(8192)
                if not chunk:
                    eof = True
                    break
                text = decoder.decode(chunk)
                if text:
                    queue.put((text, tag))
            tail = decoder.decode(b"", final=True)
            if tail:
                queue.put((tail, tag))
        except Exception:
            pass
        finally:
            if eof:
                try:
                    stream.close()
                except Exception:
                    pass

    def _poll_term(self, term):
        """主线程轮询：把该终端子进程输出显示到对应标签页；结束后清理"""
        if term not in self._terms:
            return
        try:
            while True:
                line, tag = term["queue"].get_nowait()
                self._append_term(term, line, tag)
        except queue.Empty:
            pass

        proc = term["proc"]
        if proc is not None and proc.poll() is not None:
            code = proc.poll()
            self._append_term(term, f"\n[程序已结束，退出码 {code}]\n")
            self._suggest_missing_module(term)
            term["done"] = True
            term["proc"] = None
            if term.get("tmp_file") and os.path.exists(term["tmp_file"]):
                try:
                    os.remove(term["tmp_file"])
                except OSError:
                    pass
                term["tmp_file"] = None
            self._sync_term_input_state(term)
            return
        self.root.after(100, lambda: self._poll_term(term))

    def _suggest_missing_module(self, term):
        """若报错是缺少模块，给出安装命令提示"""
        out = term["out"].get("1.0", "end-1c")
        m = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", out)
        if m:
            mod_name = m.group(1)
            self._append_term(
                term,
                f"提示：缺少模块 {mod_name}，可在命令行运行  pip install {mod_name}  后重试。\n",
                "err",
            )

    def stop_run(self):
        """强制终止当前选中终端的程序"""
        term = self._current_term()
        if term is None:
            return
        proc = term["proc"]
        if proc is not None and proc.poll() is None:
            proc.kill()
            self._append_term(term, "\n[已手动停止]\n", "err")
        else:
            self._append_term(term, "[当前终端没有正在运行的程序]\n", "err")

    # ----------------------------------------------------------------
    # 终端面板（VSCode 风格：多开 / 切换 / 关闭）
    # ----------------------------------------------------------------
    def _ensure_term_panel(self):
        """创建（或重新显示）底部终端面板"""
        if hasattr(self, "term_panel"):
            self.term_panel.pack(side=tk.BOTTOM, fill=tk.X)
            return self.term_notebook

        panel = tk.Frame(self.root, bg="#1e1e1e", height=220)
        panel.pack(side=tk.BOTTOM, fill=tk.X)
        panel.pack_propagate(False)   # 面板高度由 config 决定，不被内容撑高
        self.term_panel = panel
        self._term_h = 220

        # 工具栏：新终端（可选择 Python/CMD/PowerShell）/ ＋/－ 调大小 / 终止 / 清屏 / 关闭 / 隐藏面板
        bar = tk.Frame(panel, bg="#252526")
        bar.pack(fill=tk.X)
        mb = ttk.Menubutton(bar, text="+ 新终端 ▾")
        new_menu = tk.Menu(mb, tearoff=0)
        new_menu.add_command(label="Python 终端（输入中文可翻译）", command=self._start_repl_term)
        new_menu.add_command(label="CMD 终端",
                             command=lambda: self._start_shell_term("cmd"))
        new_menu.add_command(label="PowerShell 终端",
                             command=lambda: self._start_shell_term("powershell"))
        mb["menu"] = new_menu
        mb.pack(side=tk.LEFT, padx=2, pady=2)
        # 用 ＋/－ 按钮调面板高度（拖拽不可靠，按钮最稳）
        ttk.Button(bar, text="＋", width=3,
                   command=lambda: self._term_resize(40)).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(bar, text="－", width=3,
                   command=lambda: self._term_resize(-40)).pack(side=tk.LEFT, padx=2, pady=2)
        self._term_size_lbl = tk.Label(bar, text="220px", bg="#252526", fg="#9cdcfe",
                                       font=(FONT_FAMILY, 9))
        self._term_size_lbl.pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="终止", command=self.stop_run).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(bar, text="清屏", command=self.clear_term).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(bar, text="关闭", command=self.close_term).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(bar, text="隐藏面板", command=self._hide_run_panel).pack(side=tk.LEFT, padx=2, pady=2)

        nb = ttk.Notebook(panel)
        nb.pack(fill=tk.BOTH, expand=True)
        self.term_notebook = nb
        return nb

    def _term_resize(self, delta):
        """终端面板变大/变小（＋/－ 按钮）：每次 ±40px，下限 80"""
        try:
            h = int(self._term_h) + delta
        except Exception:
            h = 220
        h = max(80, min(700, h))
        self._term_h = h
        self.term_panel.config(height=h)
        self.term_panel.pack_propagate(False)
        self.root.update_idletasks()
        try:
            self._term_size_lbl.config(text=f"{h}px")
        except Exception:
            pass

    def _new_term_page(self, title):
        """在终端面板新建一个标签页，返回终端会话 dict"""
        page = tk.Frame(self.term_notebook, bg="#1e1e1e")
        self.term_notebook.add(page, text=title)

        out = tk.Text(page, height=10, bg="#1e1e1e", fg="#d4d4d4",
                      insertbackground="#d4d4d4", relief=tk.FLAT,
                      font=(FONT_FAMILY, 11), padx=6, pady=4)
        sb = ttk.Scrollbar(page, orient=tk.VERTICAL, command=out.yview)
        out.config(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        out.pack(fill=tk.BOTH, expand=True)
        out.tag_configure("err", foreground="#f48771")   # 错误：橙红
        out.tag_configure("in", foreground="#9cdcfe")    # 用户输入：浅蓝

        term = {
            "kind": "run", "proc": None, "queue": queue.Queue(),
            "out": out, "title": title, "done": False,
            "tmp_file": None, "frame": page,
            "send_from": "1.0",   # 用户输入起点：之前的文本是程序输出区（只读保护）
        }
        # 合并终端模式：直接在最下面打字，回车发送（像 VSCode 终端）
        out.bind("<Return>", lambda e, t=term: self._send_input(t))
        out.bind("<KeyPress>", lambda e, t=term: self._guard_term(t))
        out.bind("<BackSpace>", lambda e, t=term: self._guard_term(t))
        out.bind("<Delete>", lambda e, t=term: self._guard_term(t))
        out.bind("<Button-1>", lambda e, t=term: self._guard_click(t))
        # 新终端自动聚焦到控制台末尾，运行后直接打字就能输入
        self.root.after(120, lambda: self._focus_term(term))
        self._terms.append(term)
        self.term_notebook.select(page)
        return term

    def _focus_term(self, term):
        """光标移到控制台末尾并聚焦（新终端 / 切换标签后）"""
        try:
            out = term["out"]
            out.mark_set("insert", "end-1c")
            out.see("end")
            if out.cget("state") != "disabled":
                out.focus_set()
        except Exception:
            pass

    def _guard_click(self, term):
        """点击程序输出区 → 光标跳回输入区末尾（防误删输出）"""
        try:
            out = term["out"]
            if out.index("insert") < out.index(term["send_from"]):
                out.mark_set("insert", "end-1c")
        except Exception:
            pass

    def _guard_term(self, term):
        """在程序输出区里按键/删除 → 拦截并跳回输入区（防误删输出）"""
        try:
            out = term["out"]
            if out.index("insert") < out.index(term["send_from"]):
                out.mark_set("insert", "end-1c")
                return "break"
        except Exception:
            pass
        return None

    def _current_term(self):
        """返回当前选中标签页对应的终端（无则 None）"""
        if not self._terms:
            return None
        try:
            sel = self.term_notebook.select()
        except Exception:
            return None
        for t in self._terms:
            if str(t["frame"]) == sel:
                return t
        return self._terms[-1]

    def _append_term(self, term, text, tag=None):
        """程序输出插入到输入区之前：send_from 之后永远只是用户输入"""
        out = term["out"]
        try:
            sf = out.index(term["send_from"])
        except Exception:
            sf = "end"
        out.insert(sf, text, tag)
        # 输出插入后，输入区起点跟着后移
        term["send_from"] = out.index(f"{sf}+{len(text)}c")
        out.see(sf)

    def _sync_term_input_state(self, term):
        """程序结束后锁定控制台（VSCode 感：进程死了不能再敲）"""
        state = "disabled" if term["done"] else "normal"
        try:
            term["out"].config(state=state)
        except Exception:
            pass

    def clear_term(self):
        """清空当前终端输出"""
        term = self._current_term()
        if term is None:
            return
        term["out"].delete("1.0", tk.END)
        term["send_from"] = "1.0"

    def close_term(self):
        """关闭当前终端标签页：终止进程并删除页面"""
        term = self._current_term()
        if term is None:
            return
        self._close_term(term)

    def _close_term(self, term):
        """按终端对象关闭标签页（供按钮和自动清理共用）"""
        proc = term["proc"]
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
        if term.get("tmp_file") and os.path.exists(term["tmp_file"]):
            try:
                os.remove(term["tmp_file"])
            except OSError:
                pass
        try:
            self.term_notebook.forget(term["frame"])
        except Exception:
            pass
        if term in self._terms:
            self._terms.remove(term)
        term["done"] = True
        # 全部关完就把面板隐藏（再运行/新终端会自动弹回）
        if not self._terms:
            self._hide_run_panel()

    def _hide_run_panel(self):
        """隐藏终端面板（再运行/新终端会自动弹回）"""
        self.term_panel.pack_forget()

    def _send_input(self, term=None):
        """把控制台末尾的用户输入发给对应终端正在运行的程序。
        输入已经直接显示在控制台里（不再回显），回车后补一个换行，
        程序输出就会显示在输入的下一行。
        """
        if term is None:
            term = self._current_term()
        if term is None:
            return
        out = term["out"]
        if out.cget("state") == "disabled":
            return
        try:
            end = out.index("end-1c")
            text = out.get(term["send_from"], end)
        except Exception:
            return
        proc = term["proc"]
        # PowerShell 终端：逐条命令子进程执行
        if term["kind"] == "shell" and term.get("shell") == "powershell":
            self._run_ps_command(term, text)
        elif proc is not None and proc.poll() is None:
            try:
                # REPL 终端里输入中文也会自动翻译成 Python 再执行
                send = text
                if term["kind"] == "repl":
                    send = self.translate_to_python(text).rstrip("\n")
                proc.stdin.write(send + "\n")
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                self._append_term(term, "[程序已结束，无法输入]\n", "err")
                term["done"] = True
                self._sync_term_input_state(term)
        else:
            self._append_term(term, "[当前终端没有正在运行的程序]\n", "err")
        # 回车换行：在输入末尾（end 是发送前的末尾）补一个换行，
        # 程序输出会追加在下一行
        try:
            out.insert(end, "\n")
        except Exception:
            pass
        try:
            term["send_from"] = out.index("end-1c")
        except Exception:
            pass

    # ----------------------------------------------------------------
    # 翻译预览
    # ----------------------------------------------------------------
    def show_translate_preview(self):
        """弹出窗口，显示当前代码翻译成标准 Python 后的结果"""
        code = self.text.get("1.0", "end-1c")
        py_code = self.translate_to_python(code)
        win = tk.Toplevel(self.root)
        win.title("翻译为 Python 预览")
        win.geometry("720x480")
        txt = tk.Text(win, wrap=tk.NONE, font=("Consolas", 12), padx=8, pady=8)
        sb_y = ttk.Scrollbar(win, orient=tk.VERTICAL, command=txt.yview)
        sb_x = ttk.Scrollbar(win, orient=tk.HORIZONTAL, command=txt.xview)
        txt.config(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert("1.0", py_code)
        txt.config(state=tk.DISABLED)

    # ==================================================================
    # 帮助
    # ==================================================================
    def show_about(self):
        messagebox.showinfo(
            "关于",
            f"{APP_TITLE} v{APP_VERSION}\n\n"
            "一个基于 Python Tkinter 的简单中文文本编辑器。\n\n"
            "功能：新建 / 打开 / 保存 / 撤销 / 重做 /\n"
            "查找 / 替换 / 行号 / 字数统计 / 编码切换 /\n"
            "语法高亮 / 中文编程 / 一键运行（F5）\n\n"
            "中文编程示例：\n"
            "  输出(\"你好\")  # 等价于 print(\"你好\")\n"
            "  如果 x 大于 0：  # 等价于 if x > 0:\n"
            "  导入 math        # 等价于 import math\n"
            "  从 math 导入 sqrt  # 等价于 from math import sqrt\n"
            "（打印 也仍然可用，新旧写法都支持）\n"
            "支持编码：UTF-8、GBK（打开时自动识别）",
        )

    def show_contact(self):
        """帮助 → 联系我们：显示 B 站主页与邮箱，可一键打开 / 复制"""
        dlg = tk.Toplevel(self.root)
        dlg.title("联系我们")
        dlg.geometry("480x240")
        dlg.resizable(False, False)
        dlg.configure(bg=self._theme["root_bg"])
        dlg.transient(self.root)

        tk.Label(dlg, text="联系我们", font=(FONT_FAMILY, 16, "bold"),
                 bg=self._theme["root_bg"], fg=self._theme["status_fg"]
                 if self._theme_name == "浅色" else "#9cdcfe").pack(pady=(18, 8))

        tk.Label(dlg, text="B 站主页：space.bilibili.com/1557100135",
                 font=(FONT_FAMILY, 11),
                 bg=self._theme["root_bg"], fg=self._theme["editor_fg"]).pack(pady=3)
        tk.Label(dlg, text="邮箱：huang_dev_lab@163.com",
                 font=(FONT_FAMILY, 11),
                 bg=self._theme["root_bg"], fg=self._theme["editor_fg"]).pack(pady=3)
        tk.Label(dlg, text="（遇到问题欢迎留言，一起玩中文编程～）",
                 font=(FONT_FAMILY, 9),
                 bg=self._theme["root_bg"],
                 fg=self._theme["line_fg"]).pack(pady=(6, 10))

        row = tk.Frame(dlg, bg=self._theme["root_bg"])
        row.pack(pady=6)
        tk.Button(row, text="打开 B 站主页", command=lambda: webbrowser.open(
            "https://space.bilibili.com/1557100135"),
            font=(FONT_FAMILY, 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(row, text="复制邮箱", command=lambda: (
            dlg.clipboard_clear(), dlg.clipboard_append("huang_dev_lab@163.com"),
            messagebox.showinfo("已复制", "邮箱已复制到剪贴板：huang_dev_lab@163.com")),
            font=(FONT_FAMILY, 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(row, text="关闭", command=dlg.destroy,
                  font=(FONT_FAMILY, 10)).pack(side=tk.LEFT, padx=5)


def main():
    root = tk.Tk()
    app = ChineseEditor(root)
    # 支持命令行参数：双击 .cnpy 文件 / exe 后跟文件路径 → 直接打开
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        path = os.path.abspath(sys.argv[1])
        if os.path.isfile(path):
            app._open_path(path)
    # 自检模式：--test 时 1.5 秒后自动关闭，用于验证程序能正常启动
    if "--test" in sys.argv:
        root.after(1500, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
