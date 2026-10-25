# -*- coding: utf-8 -*-
"""
中文编辑器 安装程序
====================
把 中文编辑器.exe 安装到用户目录（无需管理员权限），自动：
  · 复制主程序 / 卸载 bat / 图标到安装目录
  · 创建桌面快捷方式 / 开始菜单快捷方式（可选）
  · 关联 .cnpy 文件（双击用中文编辑器打开，图标自动更换）
  · 写入卸载信息（控制面板"应用和功能"可卸载，卸载入口是配套的卸载 bat：
    只清理快捷方式与文件关联，程序文件由用户手动删除）
  · 重复安装检测：目标目录已装过则先提示，确认后覆盖安装
打包方式（PyInstaller，--add-data 带上 中文编辑器.exe、卸载 bat 与 图标）：
  pyinstaller --onefile --windowed --icon 中文编辑器.ico --name 中文编辑器安装程序
             --add-data "dist\中文编辑器.exe;dist"
             --add-data "中文编辑器.ico;."
             --add-data "卸载中文编辑器.bat;."
             安装程序.py
"""
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "中文编辑器"
APP_VERSION = "1.0"
PROG_ID = "CNEditor.cnpy"
DEFAULT_DEST = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Programs", APP_NAME,
)


def base_dir():
    """打包成 exe 时资源解压目录；直接跑脚本时是脚本所在目录"""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def resource(*parts):
    """定位资源文件：_MEIPASS → 脚本同目录 → 脚本上级 → 各层的 assets/ 子目录"""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    for d in (base_dir(), here, os.path.join(here, "assets"),
              root, os.path.join(root, "assets")):
        p = os.path.join(d, *parts)
        if os.path.exists(p):
            return p
    return os.path.join(base_dir(), *parts)


def _ps(script):
    """执行一段 PowerShell（创建快捷方式 / 写注册表）"""
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=False, timeout=60,
    )


def make_shortcut(lnk_path, target):
    """创建 .lnk 快捷方式（通过 WScript.Shell COM）"""
    ps = (
        f"$ws = New-Object -ComObject WScript.Shell;"
        f"$s = $ws.CreateShortcut('{lnk_path}');"
        f"$s.TargetPath = '{target}';"
        f"$s.IconLocation = '{target},0';"
        f"$s.WorkingDirectory = '{os.path.dirname(target)}';"
        f"$s.Save()"
    )
    _ps(ps)


def write_assoc(exe):
    """把 .cnpy 关联到指定 exe（HKCU，无需管理员）"""
    ps = (
        "$rk=[Microsoft.Win32.Registry]::CurrentUser;"
        f"$k=$rk.CreateSubKey('Software\\Classes\\.cnpy');"
        f"$k.SetValue('','{PROG_ID}');$k.Close();"
        f"$k=$rk.CreateSubKey('Software\\Classes\\{PROG_ID}');"
        f"$k.SetValue('','{APP_NAME}文件');$k.Close();"
        f"$k=$rk.CreateSubKey('Software\\Classes\\{PROG_ID}\\DefaultIcon');"
        f"$k.SetValue('','\"{exe}\",0');$k.Close();"
        f"$k=$rk.CreateSubKey('Software\\Classes\\{PROG_ID}\\shell\\open\\command');"
        f"$k.SetValue('','\"{exe}\" \"%1\"');$k.Close();"
    )
    _ps(ps)


def write_uninstall(exe, dest):
    """写入控制面板卸载信息，卸载入口指向安装目录里的卸载 bat"""
    uninst_bat = os.path.join(dest, f"卸载{APP_NAME}.bat")
    ps = (
        "$rk=[Microsoft.Win32.Registry]::CurrentUser;"
        "$k=$rk.CreateSubKey('Software\\Microsoft\\Windows\\CurrentVersion\\"
        f"Uninstall\\{APP_NAME}');"
        f"$k.SetValue('DisplayName','{APP_NAME}');"
        f"$k.SetValue('DisplayVersion','{APP_VERSION}');"
        f"$k.SetValue('Publisher','{APP_NAME}');"
        f"$k.SetValue('InstallLocation','{dest}');"
        f"$k.SetValue('DisplayIcon','\"{exe}\",0');"
        f"$k.SetValue('UninstallString','\"{uninst_bat}\"');"
        f"$k.SetValue('NoModify',1);$k.SetValue('NoRepair',1);$k.Close();"
    )
    _ps(ps)


def do_install(dest, make_desktop=True, make_startmenu=True, do_assoc=True):
    """执行安装，返回 (ok, 消息)"""
    try:
        os.makedirs(dest, exist_ok=True)
        exe = os.path.join(dest, f"{APP_NAME}.exe")
        shutil.copy2(resource("dist", f"{APP_NAME}.exe"), exe)
        # 卸载入口：复制卸载 bat（只清理快捷方式与关联，主体由用户手动删）
        uninst_bat = os.path.join(dest, f"卸载{APP_NAME}.bat")
        shutil.copy2(resource(f"卸载{APP_NAME}.bat"), uninst_bat)
        ico = resource(f"{APP_NAME}.ico")
        if os.path.isfile(ico):
            shutil.copy2(ico, os.path.join(dest, f"{APP_NAME}.ico"))

        if make_desktop:
            make_shortcut(
                os.path.join(os.path.expanduser("~"), "Desktop", f"{APP_NAME}.lnk"), exe)
        if make_startmenu:
            sm = os.path.join(os.environ.get("APPDATA", ""),
                              "Microsoft", "Windows", "Start Menu", "Programs")
            if os.path.isdir(sm):
                make_shortcut(os.path.join(sm, f"{APP_NAME}.lnk"), exe)
        if do_assoc:
            write_assoc(exe)
        write_uninstall(exe, dest)
        return True, f"安装完成！已安装到：\n{dest}"
    except Exception as e:
        return False, f"安装失败：\n{e}"


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION} 安装程序")
        self.geometry("520x430")
        self.resizable(False, False)
        self.configure(bg="#f5f7fa")
        self._build()

    def _build(self):
        pad = {"padx": 20, "pady": 8}
        tk.Label(self, text=f"安装 {APP_NAME} v{APP_VERSION}",
                 font=("Microsoft YaHei", 18, "bold"), bg="#f5f7fa",
                 fg="#2B5980").pack(anchor="w", **pad)
        tk.Label(self, text="基于 Python 的中文编程编辑器，安装到用户目录，无需管理员权限。",
                 font=("Microsoft YaHei", 10), bg="#f5f7fa", fg="#555").pack(anchor="w", padx=20)

        tk.Label(self, text="安装位置：", font=("Microsoft YaHei", 10),
                 bg="#f5f7fa").pack(anchor="w", padx=20)
        row = tk.Frame(self, bg="#f5f7fa")
        row.pack(fill="x", padx=20)
        self.dest_var = tk.StringVar(value=DEFAULT_DEST)
        tk.Entry(row, textvariable=self.dest_var, font=("Microsoft YaHei", 10)).pack(
            side="left", fill="x", expand=True)
        tk.Button(row, text="浏览…", command=self._browse,
                  font=("Microsoft YaHei", 9)).pack(side="left", padx=(8, 0))

        self.desk_var = tk.BooleanVar(value=True)
        self.menu_var = tk.BooleanVar(value=True)
        self.assoc_var = tk.BooleanVar(value=True)
        for var, txt in [
            (self.desk_var, "创建桌面快捷方式"),
            (self.menu_var, "创建开始菜单快捷方式"),
            (self.assoc_var, "关联 .cnpy 文件（双击用编辑器打开）"),
        ]:
            tk.Checkbutton(self, text=txt, variable=var, bg="#f5f7fa",
                           font=("Microsoft YaHei", 10),
                           activebackground="#f5f7fa").pack(anchor="w", padx=22, pady=2)

        btn_row = tk.Frame(self, bg="#f5f7fa")
        btn_row.pack(fill="x", padx=20, pady=(18, 6))
        tk.Button(btn_row, text="开始安装", command=self._install,
                  font=("Microsoft YaHei", 11, "bold"), bg="#2B5980", fg="white",
                  activebackground="#3a6ea5", activeforeground="white",
                  padx=18, pady=4).pack(side="left")
        tk.Button(btn_row, text="取消", command=self.destroy,
                  font=("Microsoft YaHei", 10)).pack(side="left", padx=(10, 0))

        self.status = tk.Label(self, text="", font=("Microsoft YaHei", 9),
                               bg="#f5f7fa", fg="#666", justify="left")
        self.status.pack(anchor="w", padx=20, pady=(6, 0))

    def _browse(self):
        d = filedialog.askdirectory(title="选择安装位置")
        if d:
            self.dest_var.set(os.path.join(d, APP_NAME))

    def _install(self):
        dest = self.dest_var.get().strip()
        if not dest:
            messagebox.showwarning("提示", "请填写安装位置。")
            return
        # 重复安装检测：目标目录已存在主程序则先询问
        if os.path.isfile(os.path.join(dest, f"{APP_NAME}.exe")):
            if not messagebox.askyesno(
                    "检测到已安装",
                    f"安装目录已存在 {APP_NAME}：\n{dest}\n\n"
                    "继续将覆盖安装（快捷方式 / .cnpy 关联会重建）。\n确定继续吗？"):
                return
        self.status.config(text="正在安装…")
        self.update_idletasks()
        ok, msg = do_install(
            dest,
            make_desktop=self.desk_var.get(),
            make_startmenu=self.menu_var.get(),
            do_assoc=self.assoc_var.get(),
        )
        self.status.config(text="")
        if ok:
            messagebox.showinfo("安装完成", msg + "\n\n桌面/开始菜单已创建快捷方式，.cnpy 文件已关联。")
            exe = os.path.join(dest, f"{APP_NAME}.exe")
            if messagebox.askyesno("中文编辑器", "立即打开编辑器？"):
                try:
                    subprocess.Popen([exe])
                except Exception:
                    pass
            self.destroy()
        else:
            messagebox.showerror("安装失败", msg)


if __name__ == "__main__":
    InstallerApp().mainloop()
