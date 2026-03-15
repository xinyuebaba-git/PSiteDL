from __future__ import annotations

import os
import queue
import sys
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, W, filedialog, messagebox, ttk
from typing import Callable


# ============================================================================
# Dark Orange Color Palette
# ============================================================================
class DarkOrangeColors:
    """暗黑橙色风格配色方案"""
    
    # 背景色
    BACKGROUND = "#1a1a1a"
    CARD_BACKGROUND = "#2d2d2d"
    INPUT_BACKGROUND = "#252525"
    
    # 主色调 - 橙色
    PRIMARY = "#ff6b00"
    PRIMARY_HOVER = "#ffab40"
    PRIMARY_PRESSED = "#e65c00"
    PRIMARY_GRADIENT_END = "#ff8533"
    
    # 文字颜色
    TEXT_PRIMARY = "#e0e0e0"
    TEXT_SECONDARY = "#a0a0a0"
    TEXT_BODY = "#e0e0e0"
    TEXT_DISABLED = "#505050"
    TEXT_HIGHLIGHT = "#ff9500"
    TEXT_PLACEHOLDER = "#707070"
    
    # 边框和分隔线
    BORDER = "#404040"
    BORDER_FOCUS = "#ff6b00"
    SEPARATOR = "#353535"
    
    # 功能色
    SUCCESS = "#4caf50"
    WARNING = "#ff9800"
    ERROR = "#f44336"
    PROGRESS_BACKGROUND = "#353535"
    
    # 列表选中
    LIST_SELECTION = "#ff6b00"


# ============================================================================
# Custom Styled Components - Dark Orange Theme
# ============================================================================
class DarkOrangeButton(tk.Canvas):
    """暗黑橙色风格按钮 - 支持圆角和渐变效果"""
    
    def __init__(
        self,
        master,
        text: str,
        command: Callable | None = None,
        width: int = 120,
        height: int = 44,
        style: str = "primary",
        **kwargs
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            highlightthickness=0,
            **kwargs
        )
        
        self.text = text
        self.command = command
        self.style = style  # primary, secondary, danger
        self.width = width
        self.height = height
        self.radius = 10
        self.state = "normal"  # normal, hover, pressed, disabled
        
        self._draw_button()
        self._bind_events()
    
    def _draw_button(self):
        """绘制按钮"""
        self.delete("all")
        
        if self.state == "disabled":
            bg_color = "#404040"
            text_color = DarkOrangeColors.TEXT_DISABLED
        elif self.state == "pressed":
            bg_color = DarkOrangeColors.PRIMARY_PRESSED
            text_color = "#ffffff"
        elif self.state == "hover":
            bg_color = DarkOrangeColors.PRIMARY_HOVER
            text_color = "#ffffff"
        else:
            # 根据样式选择颜色
            if self.style == "primary":
                bg_color = DarkOrangeColors.PRIMARY
            elif self.style == "danger":
                bg_color = DarkOrangeColors.ERROR
            else:  # secondary
                bg_color = DarkOrangeColors.PRIMARY
            text_color = "#ffffff"
        
        # 绘制圆角矩形背景
        self._rounded_rectangle(
            0, 0, self.width, self.height,
            self.radius,
            fill=bg_color,
            outline=""
        )
        
        # 绘制文字
        self.create_text(
            self.width // 2,
            self.height // 2,
            text=self.text,
            fill=text_color,
            font=("SF Pro Text", 15, "bold")
        )
    
    def _rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        """绘制圆角矩形"""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _bind_events(self):
        """绑定事件"""
        if self.state != "disabled":
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self.bind("<Button-1>", self._on_press)
            self.bind("<ButtonRelease-1>", self._on_release)
    
    def _on_enter(self, event):
        self.state = "hover"
        self._draw_button()
    
    def _on_leave(self, event):
        self.state = "normal"
        self._draw_button()
    
    def _on_press(self, event):
        self.state = "pressed"
        self._draw_button()
    
    def _on_release(self, event):
        self.state = "hover"
        self._draw_button()
        if self.command:
            self.command()
    
    def set_enabled(self, enabled: bool):
        """设置启用状态"""
        self.state = "normal" if enabled else "disabled"
        self._draw_button()
        if not enabled:
            self.unbind("<Enter>")
            self.unbind("<Leave>")
            self.unbind("<Button-1>")
            self.unbind("<ButtonRelease-1>")
        else:
            self._bind_events()


class DarkOrangeCard(tk.LabelFrame):
    """暗黑橙色风格卡片容器"""
    
    def __init__(self, master, title: str = "", padding: int = 16, **kwargs):
        super().__init__(
            master,
            bg=DarkOrangeColors.CARD_BACKGROUND,
            fg=DarkOrangeColors.TEXT_PRIMARY,
            padx=padding,
            pady=padding,
            **kwargs
        )
        
        self.configure(
            text=title,
            font=("SF Pro Text", 14, "bold"),
            relief=tk.FLAT,
            borderwidth=0
        )
    
    def create_separator(self, parent):
        """创建分隔线"""
        sep = tk.Frame(
            parent,
            height=1,
            bg=DarkOrangeColors.SEPARATOR
        )
        return sep


class _DarkOrangeRoundedBox(tk.Frame):
    """圆角输入容器基类，用 Canvas 绘制圆角背景并嵌入真实输入控件。"""

    def __init__(
        self,
        master,
        *,
        height: int | None = None,
        radius: int = 12,
        outer_bg: str = DarkOrangeColors.CARD_BACKGROUND,
        fill_color: str = DarkOrangeColors.INPUT_BACKGROUND,
        padding_x: int = 12,
        padding_y: int = 8,
    ):
        super().__init__(master, bg=outer_bg)
        self._radius = radius
        self._fill_color = fill_color
        self._padding_x = padding_x
        self._padding_y = padding_y
        self._focused = False

        self._canvas = tk.Canvas(
            self,
            bg=outer_bg,
            highlightthickness=0,
            borderwidth=0,
            relief=tk.FLAT,
        )
        self._canvas.pack(fill=BOTH, expand=True)
        self._window_id: int | None = None
        self._inner_widget: tk.Widget | None = None
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        if height is not None:
            tk.Frame.configure(self, height=height)
            self.pack_propagate(False)

    def _rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self._canvas.create_polygon(points, smooth=True, **kwargs)

    def _attach_widget(self, widget: tk.Widget) -> None:
        self._inner_widget = widget
        self._window_id = self._canvas.create_window(
            self._padding_x,
            self._padding_y,
            anchor="nw",
            window=widget,
        )
        widget.bind("<FocusIn>", self._on_focus_in, add="+")
        widget.bind("<FocusOut>", self._on_focus_out, add="+")

    def _on_focus_in(self, _event) -> None:
        self._focused = True
        self._redraw()

    def _on_focus_out(self, _event) -> None:
        self._focused = False
        self._redraw()

    def _on_canvas_configure(self, _event) -> None:
        self._redraw()

    def _redraw(self) -> None:
        width = max(2, self._canvas.winfo_width())
        height = max(2, self._canvas.winfo_height())
        self._canvas.delete("rounded_box")

        border_color = DarkOrangeColors.BORDER_FOCUS if self._focused else DarkOrangeColors.BORDER
        self._rounded_rectangle(
            1, 1, width - 1, height - 1, self._radius,
            fill=self._fill_color,
            outline=border_color,
            width=1,
            tags="rounded_box",
        )

        if self._window_id is not None:
            inner_width = max(1, width - self._padding_x * 2)
            inner_height = max(1, height - self._padding_y * 2)
            self._canvas.coords(self._window_id, self._padding_x, self._padding_y)
            self._canvas.itemconfigure(self._window_id, width=inner_width, height=inner_height)


class DarkOrangeEntry(_DarkOrangeRoundedBox):
    """暗黑橙色圆角输入框"""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=48, radius=12, padding_x=12, padding_y=10)
        kwargs.setdefault("bg", DarkOrangeColors.INPUT_BACKGROUND)
        kwargs.setdefault("fg", DarkOrangeColors.TEXT_BODY)
        kwargs.setdefault("insertbackground", DarkOrangeColors.PRIMARY)
        kwargs.setdefault("font", ("SF Pro Text", 15))
        self.entry = tk.Entry(
            self._canvas,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            **kwargs
        )
        self._attach_widget(self.entry)

    def get(self, *args, **kwargs):
        return self.entry.get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.entry.delete(*args, **kwargs)

    def insert(self, *args, **kwargs):
        return self.entry.insert(*args, **kwargs)

    def bind(self, sequence=None, func=None, add=None):
        return self.entry.bind(sequence, func, add)

    def config(self, *args, **kwargs):
        return self.entry.config(*args, **kwargs)

    configure = config


class DarkOrangeCombobox(_DarkOrangeRoundedBox):
    """暗黑橙色圆角下拉框"""

    _style_name = "DarkOrange.TCombobox"
    _style_ready = False

    def __init__(self, master, **kwargs):
        super().__init__(master, height=48, radius=12, padding_x=8, padding_y=8)
        style = ttk.Style()
        if not DarkOrangeCombobox._style_ready:
            style.configure(
                self._style_name,
                foreground=DarkOrangeColors.TEXT_BODY,
                fieldbackground=DarkOrangeColors.INPUT_BACKGROUND,
                background=DarkOrangeColors.INPUT_BACKGROUND,
                arrowcolor=DarkOrangeColors.TEXT_BODY,
                borderwidth=0,
                padding=4,
                font=("SF Pro Text", 14),
            )
            style.map(
                self._style_name,
                fieldbackground=[("readonly", DarkOrangeColors.INPUT_BACKGROUND)],
                foreground=[("readonly", DarkOrangeColors.TEXT_BODY)],
                selectforeground=[("readonly", DarkOrangeColors.TEXT_BODY)],
                selectbackground=[("readonly", DarkOrangeColors.INPUT_BACKGROUND)],
            )
            DarkOrangeCombobox._style_ready = True

        self.combo = ttk.Combobox(
            self._canvas,
            style=self._style_name,
            **kwargs,
        )
        self._attach_widget(self.combo)

    def bind(self, sequence=None, func=None, add=None):
        return self.combo.bind(sequence, func, add)

    def config(self, *args, **kwargs):
        return self.combo.config(*args, **kwargs)

    configure = config


class DarkOrangeText(_DarkOrangeRoundedBox):
    """暗黑橙色圆角文本框"""

    def __init__(self, master, **kwargs):
        text_height = kwargs.pop("height", None)
        fill_color = kwargs.get("bg", DarkOrangeColors.INPUT_BACKGROUND)
        fixed_height = max(120, int(text_height) * 26 + 24) if text_height is not None else None

        super().__init__(
            master,
            height=fixed_height,
            radius=12,
            padding_x=12,
            padding_y=10,
            fill_color=fill_color,
        )

        kwargs.setdefault("bg", DarkOrangeColors.INPUT_BACKGROUND)
        kwargs.setdefault("fg", DarkOrangeColors.TEXT_BODY)
        kwargs.setdefault("insertbackground", DarkOrangeColors.PRIMARY)
        kwargs.setdefault("font", ("SF Pro Text", 15))

        self.text = tk.Text(
            self._canvas,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            **kwargs
        )
        self._attach_widget(self.text)
        self._placeholder_active = False

    def set_placeholder(self, placeholder: str):
        """设置占位符文本"""
        self.delete("1.0", END)
        self.insert("1.0", placeholder)
        self.text.configure(fg=DarkOrangeColors.TEXT_PLACEHOLDER)
        self._placeholder_active = True

    def delete_placeholder(self):
        """删除占位符并恢复文字颜色"""
        if not self._placeholder_active:
            return
        content = self.get("1.0", END).strip()
        if content:
            self.delete("1.0", END)
            self.text.configure(fg=DarkOrangeColors.TEXT_BODY)
            self._placeholder_active = False

    def get(self, *args, **kwargs):
        return self.text.get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.text.delete(*args, **kwargs)

    def insert(self, *args, **kwargs):
        return self.text.insert(*args, **kwargs)

    def see(self, *args, **kwargs):
        return self.text.see(*args, **kwargs)

    def tag_configure(self, *args, **kwargs):
        return self.text.tag_configure(*args, **kwargs)

    def bind(self, sequence=None, func=None, add=None):
        return self.text.bind(sequence, func, add)

    def config(self, *args, **kwargs):
        return self.text.config(*args, **kwargs)

    configure = config


class DarkOrangeProgressbar(tk.Canvas):
    """暗黑橙色风格进度条"""
    
    def __init__(self, master, width: int = 300, height: int = 8, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            highlightthickness=0,
            **kwargs
        )
        
        self.width = width
        self.height = height
        self.radius = height // 2
        self.progress = 0
        
        self._draw_background()
        self._draw_progress()
    
    def _draw_background(self):
        """绘制背景轨道"""
        self._rounded_rectangle(
            0, 0, self.width, self.height,
            self.radius,
            fill=DarkOrangeColors.PROGRESS_BACKGROUND
        )
    
    def _draw_progress(self):
        """绘制进度"""
        self.delete("progress")
        if self.progress > 0:
            progress_width = int(self.width * self.progress / 100)
            self._rounded_rectangle(
                0, 0, progress_width, self.height,
                self.radius,
                fill=DarkOrangeColors.PRIMARY,
                tags="progress"
            )
    
    def _rounded_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        """绘制圆角矩形"""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def set_progress(self, value: float):
        """设置进度值 (0-100)"""
        self.progress = max(0, min(100, value))
        self._draw_progress()


class DarkOrangeNotebook(ttk.Notebook):
    """暗黑橙色风格标签页"""
    
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            style="DarkOrange.TNotebook",
            **kwargs
        )
        
        # 配置样式
        self.style = ttk.Style()
        self.style.configure(
            "DarkOrange.TNotebook",
            background=DarkOrangeColors.CARD_BACKGROUND,
            bordercolor=DarkOrangeColors.BORDER,
            tabmargins=[0, 0, 0, 0],
        )
        self.style.configure(
            "DarkOrange.TNotebook.Tab",
            background=DarkOrangeColors.INPUT_BACKGROUND,
            foreground=DarkOrangeColors.TEXT_SECONDARY,
            padding=[16, 8],
            font=("SF Pro Text", 13),
        )
        self.style.map(
            "DarkOrange.TNotebook.Tab",
            background=[("selected", DarkOrangeColors.PRIMARY)],
            foreground=[("selected", "#ffffff")],
        )


class CompatButton(ttk.Button):
    """兼容模式按钮，补齐 set_enabled 接口。"""

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.state(["!disabled"])
        else:
            self.state(["disabled"])


# ============================================================================
# Main Application
# ============================================================================
@dataclass
class DownloadTask:
    task_id: int
    url: str
    status: str = "pending"
    downloaded_fragments: int = 0
    total_fragments: int | None = None
    output_file: Path | None = None
    log_file: Path | None = None


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PSiteDL - 视频下载工具")
        self.root.geometry("1200x850")
        self.root.minsize(1000, 700)
        self.compat_mode = self._should_use_compat_ui()
        if self.compat_mode:
            self.root.configure(bg="#f0f0f0")
        else:
            self.root.configure(bg=DarkOrangeColors.BACKGROUND)
        
        # 加载并设置窗口图标
        self._load_icon()
        
        # 设置 DPI 感知（Windows）
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        
        self.output_dir = tk.StringVar(value=str((Path.home() / "Downloads").resolve()))
        self.browser = tk.StringVar(value="chrome")
        self.profile = tk.StringVar(value="Default")
        self.capture_seconds = tk.StringVar(value="30")
        self.use_runtime_capture = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value="就绪")
        
        self.running = False
        self.next_task_id = 1
        self.tasks: dict[int, DownloadTask] = {}
        self.pending_ids: list[int] = []
        self.active_futures: dict[Future, int] = {}
        self.completed_ids: list[int] = []
        self.executor: ThreadPoolExecutor | None = None
        self.log_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        
        self._build_ui()
        self._poll_logs()

    def _should_use_compat_ui(self) -> bool:
        """在 macOS 自带 Tk 8.5 上启用兼容界面，避免自定义绘制丢失。"""
        if sys.platform != "darwin":
            return False
        try:
            patchlevel = self.root.tk.call("info", "patchlevel")
            parts = str(patchlevel).split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            return (major, minor) < (8, 6)
        except Exception:
            return False
    
    def _load_icon(self) -> None:
        """加载应用程序图标
        
        支持多种格式：
        - Windows: .ico
        - macOS: .icns
        - Linux: .png
        """
        try:
            # 获取图标文件路径
            script_dir = Path(__file__).parent
            project_root = script_dir.parent.parent
            assets_dir = project_root / "assets"
            loaded = False

            # 根据不同平台选择图标格式
            if os.name == "nt":  # Windows
                icon_path = assets_dir / "psitedl_icon.ico"
                if icon_path.exists():
                    self.root.iconbitmap(str(icon_path))
                    loaded = True
            elif os.name == "posix":
                # macOS/Linux: 优先使用 Tk 一定支持的 GIF，避免系统 Tk 对 PNG 的兼容问题
                for icon_path in (
                    assets_dir / "icon-64.gif",
                    assets_dir / "psitedl_icon.png",
                    assets_dir / "icon-64.png",
                ):
                    if not icon_path.exists():
                        continue
                    try:
                        icon_img = tk.PhotoImage(file=str(icon_path))
                        self.root.iconphoto(True, icon_img)
                        # 保持引用防止被垃圾回收
                        self._icon_image = icon_img
                        loaded = True
                        break
                    except Exception:
                        continue

                # macOS 额外尝试 .icns（某些 Tk 版本不支持，故仅保留占位）
                if sys.platform == "darwin":
                    icns_path = assets_dir / "icon.icns"
                    if icns_path.exists():
                        # macOS 可以通过 pyobjc 设置 dock 图标（这里不强依赖该能力）
                        pass

            if loaded:
                print("[✓] 图标加载成功")
            else:
                print("[!] 图标加载失败：未找到可用图标格式")
        except Exception as e:
            print(f"[!] 图标加载失败：{e}")
    
    def _build_ui(self) -> None:
        """构建用户界面 - 左右分栏布局"""
        if self.compat_mode:
            self._build_compat_ui()
            return
        
        # 主容器
        main_frame = tk.Frame(self.root, bg=DarkOrangeColors.BACKGROUND)
        # 在 macOS 的系统 Tk 下，place + 负尺寸偏移会导致容器被错误计算为 1x1。
        # 使用 pack + 外边距可确保主布局稳定铺满窗口。
        main_frame.pack(fill=BOTH, expand=True, padx=24, pady=24)
        
        # 1. 标题区
        self._build_header(main_frame)
        
        # 2. 左右分栏容器 (使用 PanedWindow 实现可调节分栏)
        paned = tk.PanedWindow(
            main_frame,
            orient=tk.HORIZONTAL,
            bg=DarkOrangeColors.BACKGROUND,
            relief=tk.FLAT,
            borderwidth=0,
            sashwidth=6,
            sashrelief=tk.RAISED
        )
        paned.pack(fill=BOTH, expand=True, pady=(16, 0))
        
        # 左侧操作区容器
        left_frame = tk.Frame(paned, bg=DarkOrangeColors.BACKGROUND)
        paned.add(left_frame, minsize=700, width=720)
        
        # 右侧日志区容器
        right_frame = tk.Frame(paned, bg=DarkOrangeColors.BACKGROUND)
        paned.add(right_frame, minsize=450, width=480)
        
        # 构建左侧操作区
        self._build_left_panel(left_frame)
        
        # 构建右侧日志区
        self._build_right_panel(right_frame)
        
        # 设置初始分栏比例 (60:40)
        # 设置初始分隔位置 (720px)
        # 某些 Tk 版本在初次布局阶段调用 sash_pos 会抛 TclError
        try:
            paned.sash_pos(0, 720)
        except Exception:
            pass

    def _build_compat_ui(self) -> None:
        """为 macOS 系统 Tk 8.5 构建稳定显示的原生界面。"""
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=BOTH, expand=True)
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(1, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(
            header,
            text="PSiteDL 视频下载工具",
            font=("Helvetica", 20, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(
            header,
            text="兼容模式",
            foreground="#666666",
        ).pack(side=tk.LEFT, padx=(12, 0), pady=(6, 0))

        left = ttk.Frame(main)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)

        right = ttk.Frame(main)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        url_frame = ttk.LabelFrame(left, text="待下载 URL")
        url_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        url_frame.columnconfigure(0, weight=1)
        ttk.Label(
            url_frame,
            text="每行一个播放页 URL",
            foreground="#666666",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))
        self.url_text = tk.Text(url_frame, height=6, wrap=tk.WORD)
        self.url_text.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        settings = ttk.LabelFrame(left, text="设置")
        settings.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        settings.columnconfigure(1, weight=1)
        settings.columnconfigure(3, weight=1)

        ttk.Label(settings, text="浏览器").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        browser_combo = ttk.Combobox(
            settings,
            textvariable=self.browser,
            values=["chrome", "chromium", "edge", "brave"],
            state="readonly",
        )
        browser_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 6))

        ttk.Label(settings, text="配置文件").grid(row=0, column=2, sticky="w", padx=(0, 10), pady=(10, 6))
        ttk.Entry(settings, textvariable=self.profile).grid(
            row=0, column=3, sticky="ew", padx=(0, 10), pady=(10, 6)
        )

        ttk.Label(settings, text="输出目录").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(settings, textvariable=self.output_dir).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=(0, 10), pady=6
        )
        ttk.Button(settings, text="浏览", command=self._pick_output_dir).grid(
            row=1, column=3, sticky="ew", padx=(0, 10), pady=6
        )

        ttk.Label(settings, text="运行时探测秒数").grid(row=2, column=0, sticky="w", padx=10, pady=(6, 10))
        ttk.Entry(settings, textvariable=self.capture_seconds).grid(
            row=2, column=1, sticky="ew", padx=(0, 10), pady=(6, 10)
        )
        ttk.Checkbutton(
            settings,
            text="启用运行时探测（会打开浏览器并抓播放请求）",
            variable=self.use_runtime_capture,
        ).grid(row=2, column=2, columnspan=2, sticky="w", padx=(0, 10), pady=(6, 10))

        controls = ttk.Frame(left)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        controls.columnconfigure(4, weight=1)

        self.add_btn = CompatButton(controls, text="加入待下载", command=self._add_tasks)
        self.add_btn.grid(row=0, column=0, padx=(0, 8))
        self.start_btn = CompatButton(controls, text="启动下载", command=self._start_queue)
        self.start_btn.grid(row=0, column=1, padx=(0, 8))
        self.clear_pending_btn = CompatButton(controls, text="清空待下载", command=self._clear_pending)
        self.clear_pending_btn.grid(row=0, column=2, padx=(0, 8))
        CompatButton(controls, text="清空日志", command=self._clear_log).grid(row=0, column=3, padx=(0, 12))
        ttk.Label(controls, textvariable=self.status_text).grid(row=0, column=4, sticky="e")

        tasks = ttk.LabelFrame(left, text="任务管理")
        tasks.grid(row=3, column=0, sticky="nsew")
        tasks.columnconfigure(0, weight=1)
        tasks.rowconfigure(0, weight=1)

        task_tabs = ttk.Notebook(tasks)
        task_tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        pending_tab = ttk.Frame(task_tabs)
        task_tabs.add(pending_tab, text="待下载")
        pending_tab.columnconfigure(0, weight=1)
        pending_tab.rowconfigure(0, weight=1)
        self.pending_list = tk.Listbox(pending_tab)
        self.pending_list.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        active_tab = ttk.Frame(task_tabs)
        task_tabs.add(active_tab, text="下载中")
        active_tab.columnconfigure(0, weight=1)
        active_tab.rowconfigure(0, weight=1)
        self.active_tree = ttk.Treeview(
            active_tab,
            columns=("url", "progress", "status"),
            show="headings",
        )
        self.active_tree.heading("url", text="URL")
        self.active_tree.heading("progress", text="进度")
        self.active_tree.heading("status", text="状态")
        self.active_tree.column("url", width=360, anchor=W)
        self.active_tree.column("progress", width=90, anchor=W)
        self.active_tree.column("status", width=90, anchor=W)
        self.active_tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        completed_tab = ttk.Frame(task_tabs)
        task_tabs.add(completed_tab, text="已完成")
        completed_tab.columnconfigure(0, weight=1)
        completed_tab.rowconfigure(0, weight=1)
        self.completed_list = tk.Listbox(completed_tab)
        self.completed_list.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        log_frame = ttk.LabelFrame(right, text="运行日志")
        log_frame.grid(row=0, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    
    def _build_header(self, parent):
        """构建标题区"""
        header_frame = tk.Frame(parent, bg=DarkOrangeColors.BACKGROUND)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 加载标题栏图标（64x64）
        try:
            script_dir = Path(__file__).parent
            project_root = script_dir.parent.parent
            assets_dir = project_root / "assets"
            for icon_path in (assets_dir / "icon-64.gif", assets_dir / "icon-64.png"):
                if not icon_path.exists():
                    continue
                try:
                    self.header_icon = tk.PhotoImage(file=str(icon_path))
                    icon_label = tk.Label(
                        header_frame,
                        image=self.header_icon,
                        bg=DarkOrangeColors.BACKGROUND
                    )
                    icon_label.pack(side=tk.LEFT, padx=(0, 12), pady=(0, 0))
                    break
                except Exception:
                    continue
        except Exception as e:
            print(f"[!] 标题栏图标加载失败：{e}")
        
        # 主标题 - 橙色强调
        title_label = tk.Label(
            header_frame,
            text="PSiteDL",
            font=("SF Pro Display", 28, "bold"),
            fg=DarkOrangeColors.TEXT_HIGHLIGHT,
            bg=DarkOrangeColors.BACKGROUND,
            anchor="w"
        )
        title_label.pack(side=tk.LEFT)
        
        # 副标题
        subtitle_label = tk.Label(
            header_frame,
            text="视频下载工具",
            font=("SF Pro Text", 17),
            fg=DarkOrangeColors.TEXT_SECONDARY,
            bg=DarkOrangeColors.BACKGROUND,
            anchor="w"
        )
        subtitle_label.pack(side=tk.LEFT, padx=(12, 0), pady=(8, 0))
    
    def _build_left_panel(self, parent):
        """构建左侧操作区"""
        # URL 输入卡片
        self._build_url_card(parent)
        
        # 设置卡片
        self._build_settings_card(parent)
        
        # 操作按钮区
        self._build_controls_card(parent)
        
        # 任务管理卡片
        self._build_tasks_card(parent)
    
    def _build_right_panel(self, parent):
        """构建右侧日志区"""
        # 日志卡片 (占满整个右侧区域)
        self._build_log_card(parent)
    
    def _build_url_card(self, parent):
        """构建 URL 输入卡片"""
        card = DarkOrangeCard(parent, text="", padding=20)
        card.pack(fill=tk.X, pady=(0, 16))

        title_label = tk.Label(
            card,
            text="待下载 URL",
            font=("SF Pro Text", 13, "bold"),
            fg=DarkOrangeColors.TEXT_HIGHLIGHT,
            bg=DarkOrangeColors.CARD_BACKGROUND,
            anchor="w"
        )
        title_label.pack(fill=tk.X)
        
        # URL 输入框
        self.url_text = DarkOrangeText(card, height=4)
        self.url_text.pack(fill=tk.X, pady=(8, 0))
        self.url_text.set_placeholder("请输入视频播放页面 URL（每行一个）")
        
        # 绑定焦点事件以清除占位符
        self.url_text.bind("<FocusIn>", lambda e: self.url_text.delete_placeholder())
    
    def _build_settings_card(self, parent):
        """构建设置卡片"""
        card = DarkOrangeCard(parent, text="设置", padding=20)
        card.pack(fill=tk.X, pady=(0, 16))
        
        # 设置网格布局
        settings_frame = tk.Frame(card, bg=DarkOrangeColors.CARD_BACKGROUND)
        settings_frame.pack(fill=tk.X)
        
        # 第一行：浏览器、Profile、输出目录
        row1 = tk.Frame(settings_frame, bg=DarkOrangeColors.CARD_BACKGROUND)
        row1.pack(fill=tk.X, pady=(0, 16))
        row1.grid_columnconfigure(0, weight=1, uniform="settings_row")
        row1.grid_columnconfigure(1, weight=1, uniform="settings_row")
        row1.grid_columnconfigure(2, weight=1, uniform="settings_row")
        
        # 浏览器选择
        browser_frame = self._create_setting_field(
            row1,
            "浏览器",
            ["chrome", "chromium", "edge", "brave"],
            self.browser
        )
        browser_frame.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        
        # 配置文件
        profile_frame = self._create_setting_field(
            row1,
            "配置文件",
            None,
            self.profile,
            is_entry=True
        )
        profile_frame.grid(row=0, column=1, sticky="ew", padx=(0, 16))
        
        # 输出目录
        output_frame = self._create_setting_field(
            row1,
            "输出目录",
            None,
            self.output_dir,
            is_entry=True,
            has_button=True,
            button_text="浏览",
            button_command=self._pick_output_dir
        )
        output_frame.grid(row=0, column=2, sticky="ew")
        
        # 第二行：运行时探测
        row2 = tk.Frame(settings_frame, bg=DarkOrangeColors.CARD_BACKGROUND)
        row2.pack(fill=tk.X)
        row2.grid_columnconfigure(0, weight=1)
        row2.grid_columnconfigure(1, weight=1)
        
        seconds_frame = self._create_setting_field(
            row2,
            "运行时探测秒数",
            None,
            self.capture_seconds,
            is_entry=True
        )
        seconds_frame.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        
        # 运行时探测开关 - 橙色主题
        capture_check = tk.Checkbutton(
            row2,
            text="启用运行时探测 (会打开浏览器并抓播放请求)",
            variable=self.use_runtime_capture,
            font=("SF Pro Text", 13),
            fg=DarkOrangeColors.TEXT_BODY,
            bg=DarkOrangeColors.CARD_BACKGROUND,
            selectcolor=DarkOrangeColors.CARD_BACKGROUND,
            activebackground=DarkOrangeColors.CARD_BACKGROUND,
            activeforeground=DarkOrangeColors.TEXT_BODY
        )
        capture_check.grid(row=0, column=1, sticky="w", padx=(16, 0), pady=(34, 0))
    
    def _create_setting_field(
        self,
        parent,
        label: str,
        values: list[str] | None,
        variable: tk.StringVar,
        is_entry: bool = False,
        has_button: bool = False,
        button_text: str = "",
        button_command: Callable | None = None
    ):
        """创建设置字段"""
        frame = tk.Frame(parent, bg=DarkOrangeColors.CARD_BACKGROUND)
        
        # 标签 - 橙色强调
        label_widget = tk.Label(
            frame,
            text=label,
            font=("SF Pro Text", 13, "bold"),
            fg=DarkOrangeColors.TEXT_HIGHLIGHT,
            bg=DarkOrangeColors.CARD_BACKGROUND,
            anchor="w"
        )
        label_widget.pack(fill=tk.X, pady=(0, 8))
        
        # 输入控件
        if values:
            combo = DarkOrangeCombobox(
                frame,
                textvariable=variable,
                values=values,
                state="readonly",
            )
            combo.pack(fill=tk.X)
        elif has_button:
            # 输入框 + 按钮
            entry_frame = tk.Frame(frame, bg=DarkOrangeColors.CARD_BACKGROUND)
            entry_frame.pack(fill=tk.X)
            
            entry = DarkOrangeEntry(entry_frame, textvariable=variable)
            entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))
            
            button = DarkOrangeButton(
                entry_frame,
                text=button_text,
                command=button_command,
                width=80,
                height=44,
                style="secondary"
            )
            button.pack(side=tk.RIGHT)
        else:
            # 纯输入框
            entry = DarkOrangeEntry(frame, textvariable=variable)
            entry.pack(fill=tk.X)
        
        return frame
    
    def _build_controls_card(self, parent):
        """构建操作按钮卡片"""
        card = DarkOrangeCard(parent, text="", padding=20)
        card.pack(fill=tk.X, pady=(0, 16))
        
        controls_frame = tk.Frame(card, bg=DarkOrangeColors.CARD_BACKGROUND)
        controls_frame.pack(fill=tk.X)
        
        # 按钮组
        self.add_btn = DarkOrangeButton(
            controls_frame,
            text="加入待下载",
            command=self._add_tasks,
            width=140,
            height=44,
            style="secondary"
        )
        self.add_btn.pack(side=tk.LEFT, padx=(0, 12))
        
        self.start_btn = DarkOrangeButton(
            controls_frame,
            text="启动下载",
            command=self._start_queue,
            width=140,
            height=44,
            style="primary"
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 12))
        
        self.clear_pending_btn = DarkOrangeButton(
            controls_frame,
            text="清空待下载",
            command=self._clear_pending,
            width=140,
            height=44,
            style="danger"
        )
        self.clear_pending_btn.pack(side=tk.LEFT, padx=(0, 12))
        
        # 清空日志按钮
        clear_log_btn = DarkOrangeButton(
            controls_frame,
            text="清空日志",
            command=self._clear_log,
            width=100,
            height=44,
            style="secondary"
        )
        clear_log_btn.pack(side=tk.LEFT, padx=(0, 24))
        
        # 状态显示 - 橙色强调
        status_label = tk.Label(
            controls_frame,
            textvariable=self.status_text,
            font=("SF Pro Text", 14),
            fg=DarkOrangeColors.TEXT_HIGHLIGHT,
            bg=DarkOrangeColors.CARD_BACKGROUND,
            anchor="w"
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _build_tasks_card(self, parent):
        """构建任务管理卡片"""
        card = DarkOrangeCard(parent, text="任务管理", padding=20)
        card.pack(fill=BOTH, expand=True, pady=(0, 16))
        
        # 标签页 - 暗黑橙色风格
        task_tabs = DarkOrangeNotebook(card, padding=0)
        task_tabs.pack(fill=BOTH, expand=True)
        
        # 待下载任务
        pending_tab = tk.Frame(task_tabs, bg=DarkOrangeColors.CARD_BACKGROUND)
        task_tabs.add(pending_tab, text="  待下载  ")
        
        self.pending_list = tk.Listbox(
            pending_tab,
            font=("SF Pro Text", 14),
            fg=DarkOrangeColors.TEXT_BODY,
            bg=DarkOrangeColors.INPUT_BACKGROUND,
            selectbackground=DarkOrangeColors.LIST_SELECTION,
            selectforeground="#ffffff",
            highlightthickness=0,
            borderwidth=0,
            activestyle="none"
        )
        self.pending_list.pack(fill=BOTH, expand=True, padx=8, pady=8)
        
        # 正在下载任务
        active_tab = tk.Frame(task_tabs, bg=DarkOrangeColors.CARD_BACKGROUND)
        task_tabs.add(active_tab, text="  下载中  ")
        
        self.active_tree = ttk.Treeview(
            active_tab,
            columns=("url", "progress", "status"),
            show="headings",
            height=10
        )
        self.active_tree.heading("url", text="URL")
        self.active_tree.heading("progress", text="进度")
        self.active_tree.heading("status", text="状态")
        self.active_tree.column("url", width=600, anchor=W)
        self.active_tree.column("progress", width=120, anchor=W)
        self.active_tree.column("status", width=140, anchor=W)
        self.active_tree.pack(fill=BOTH, expand=True, padx=8, pady=8)
        
        # 配置 Treeview 样式 (使用 ttk.Style)
        style = ttk.Style()
        style.configure(
            "DarkOrange.Treeview",
            background=DarkOrangeColors.INPUT_BACKGROUND,
            foreground=DarkOrangeColors.TEXT_BODY,
            fieldbackground=DarkOrangeColors.INPUT_BACKGROUND,
            font=("SF Pro Text", 13)
        )
        style.configure(
            "DarkOrange.Treeview.Heading",
            background=DarkOrangeColors.CARD_BACKGROUND,
            foreground=DarkOrangeColors.TEXT_PRIMARY,
            font=("SF Pro Text", 13, "bold")
        )
        self.active_tree.configure(style="DarkOrange.Treeview")
        
        # 设置行样式
        self.active_tree.tag_configure("default", background=DarkOrangeColors.INPUT_BACKGROUND)
        
        # 已完成任务
        completed_tab = tk.Frame(task_tabs, bg=DarkOrangeColors.CARD_BACKGROUND)
        task_tabs.add(completed_tab, text="  已完成  ")
        
        self.completed_list = tk.Listbox(
            completed_tab,
            font=("SF Pro Text", 14),
            fg=DarkOrangeColors.TEXT_BODY,
            bg=DarkOrangeColors.INPUT_BACKGROUND,
            selectbackground=DarkOrangeColors.SUCCESS,
            selectforeground="#ffffff",
            highlightthickness=0,
            borderwidth=0,
            activestyle="none"
        )
        self.completed_list.pack(fill=BOTH, expand=True, padx=8, pady=8)
    
    def _build_log_card(self, parent):
        """构建日志卡片 - 右侧全屏日志区"""
        card = DarkOrangeCard(parent, text="运行日志", padding=20)
        card.pack(fill=BOTH, expand=True)
        
        # 日志文本框 - 橙色文字 @ 深色背景
        self.log_text = DarkOrangeText(
            card,
            font=("SF Mono", 12),
            fg="#ff9500",  # 橙色文字
            bg="#1e1e1e",  # 深色背景
            state=tk.DISABLED
        )
        self.log_text.pack(fill=BOTH, expand=True)
        
        # 配置日志标签颜色
        self.log_text.tag_configure("info", foreground="#ff9500")
        self.log_text.tag_configure("progress", foreground="#ffab40")
        self.log_text.tag_configure("warning", foreground="#ff9800")
        self.log_text.tag_configure("error", foreground="#f44336")
        self.log_text.tag_configure("task", foreground="#4fc3f7")
        self.log_text.tag_configure("success", foreground="#4caf50")
    
    def _clear_log(self) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", END)
        self.log_text.config(state=tk.DISABLED)
    
    def _pick_output_dir(self) -> None:
        p = filedialog.askdirectory(title="选择输出目录")
        if p:
            self.output_dir.set(str(Path(p).resolve()))
    
    def _add_tasks(self) -> None:
        raw = self.url_text.get("1.0", END)
        urls = [x.strip() for x in raw.splitlines() if x.strip()]
        if not urls:
            messagebox.showwarning("提示", "请填写至少一个 URL。")
            return
        existing = {t.url for t in self.tasks.values()}
        added = 0
        for url in urls:
            if url in existing:
                continue
            tid = self.next_task_id
            self.next_task_id += 1
            task = DownloadTask(task_id=tid, url=url)
            self.tasks[tid] = task
            self.pending_ids.append(tid)
            existing.add(url)
            added += 1
        self._refresh_pending_list()
        self.url_text.delete("1.0", END)
        self._append_log(f"[queue] 新增任务 {added} 个。")
    
    def _clear_pending(self) -> None:
        if self.running:
            messagebox.showwarning("提示", "下载进行中，暂不允许清空待下载。")
            return
        for tid in self.pending_ids:
            self.tasks[tid].status = "removed"
        self.pending_ids = []
        self._refresh_pending_list()
        self._append_log("[queue] 已清空待下载任务。")
    
    def _start_queue(self) -> None:
        if self.running:
            return
        if not self.pending_ids:
            messagebox.showwarning("提示", "待下载任务为空。")
            return
        out = Path(self.output_dir.get().strip()).expanduser()
        if not str(out):
            messagebox.showerror("参数错误", "请填写输出目录")
            return
        try:
            seconds = int(self.capture_seconds.get().strip())
            if seconds < 10:
                raise ValueError()
        except ValueError:
            messagebox.showerror("参数错误", "运行时探测秒数建议 >= 10")
            return
        
        self.running = True
        self.status_text.set("队列下载中...")
        self.start_btn.set_enabled(False)
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="sitegrab")
        self._dispatch_jobs()
    
    def _dispatch_jobs(self) -> None:
        if not self.running or self.executor is None:
            return
        browser = self.browser.get().strip() or "chrome"
        profile = self.profile.get().strip() or "Default"
        use_runtime_capture = bool(self.use_runtime_capture.get())
        capture_seconds = int(self.capture_seconds.get().strip())
        out_dir = Path(self.output_dir.get().strip()).expanduser().resolve()
        while len(self.active_futures) < 3 and self.pending_ids:
            tid = self.pending_ids.pop(0)
            task = self.tasks[tid]
            task.status = "running"
            self._upsert_active_row(task)
            future = self.executor.submit(
                self._run_one_task,
                tid,
                out_dir,
                capture_seconds,
                browser,
                profile,
                use_runtime_capture,
            )
            self.active_futures[future] = tid
            future.add_done_callback(lambda fut: self.log_queue.put(("__TASK_DONE__", fut)))
        self._refresh_pending_list()
        self._update_status_line()
    
    def _run_one_task(
        self,
        tid: int,
        out_dir: Path,
        seconds: int,
        browser: str,
        profile: str,
        use_runtime_capture: bool,
    ):
        from webvidgrab.site_cli import run_site_download
        
        task = self.tasks[tid]
        
        def log_func(msg: str) -> None:
            self.log_queue.put(("__TASK_LOG__", (tid, msg)))
        
        def progress(downloaded: int, total: int | None) -> None:
            self.log_queue.put(("__PROGRESS__", (tid, downloaded, total)))
        
        return run_site_download(
            page_url=task.url,
            output_dir=out_dir,
            browser=browser,
            profile=profile,
            capture_seconds=max(10, int(seconds)),
            use_runtime_capture=use_runtime_capture,
            log_func=log_func,
            progress_callback=progress,
        )
    
    def _handle_task_done(self, future: Future) -> None:
        tid = self.active_futures.pop(future, None)
        if tid is None:
            return
        task = self.tasks[tid]
        try:
            result = future.result()
        except Exception as exc:
            task.status = "failed"
            task.log_file = None
            self._append_log(f"[task-{tid}] [error] {exc}")
            self._remove_active_row(tid)
            self._update_status_line()
            self._dispatch_jobs()
            self._finish_if_idle()
            return
        
        task.log_file = result.log_file
        task.output_file = result.output_file
        if result.ok and result.output_file is not None:
            task.status = "done"
            self.completed_ids.append(tid)
            file_part = result.output_file.name
            self.completed_list.insert(END, f"#{tid} {file_part}")
            self._append_log(f"[task-{tid}] [saved] {result.output_file}")
            self._append_log(f"[task-{tid}] [log] {result.log_file}")
        else:
            task.status = "failed"
            self._append_log(f"[task-{tid}] [failed] {result.log_file}")
        
        self._remove_active_row(tid)
        self._update_status_line()
        self._dispatch_jobs()
        self._finish_if_idle()
    
    def _finish_if_idle(self) -> None:
        if self.running and not self.pending_ids and not self.active_futures:
            self.running = False
            self.status_text.set("全部任务完成")
            self.start_btn.set_enabled(True)
            if self.executor is not None:
                self.executor.shutdown(wait=False, cancel_futures=False)
                self.executor = None
    
    def _progress_text(self, task: DownloadTask) -> str:
        if task.total_fragments is None:
            if task.downloaded_fragments > 0:
                return f"{task.downloaded_fragments}/?"
            return "-"
        return f"{task.downloaded_fragments}/{task.total_fragments}"
    
    def _short_url(self, url: str, max_len: int = 80) -> str:
        if len(url) <= max_len:
            return url
        return url[: max_len - 3] + "..."
    
    def _upsert_active_row(self, task: DownloadTask) -> None:
        iid = str(task.task_id)
        values = (self._short_url(task.url), self._progress_text(task), task.status)
        if self.active_tree.exists(iid):
            self.active_tree.item(iid, values=values)
        else:
            self.active_tree.insert("", END, iid=iid, values=values)
    
    def _remove_active_row(self, tid: int) -> None:
        iid = str(tid)
        if self.active_tree.exists(iid):
            self.active_tree.delete(iid)
    
    def _refresh_pending_list(self) -> None:
        self.pending_list.delete(0, END)
        for tid in self.pending_ids:
            task = self.tasks[tid]
            self.pending_list.insert(END, f"#{tid} {self._short_url(task.url)}")
    
    def _update_status_line(self) -> None:
        if not self.running:
            return
        self.status_text.set(
            f"下载中：正在{len(self.active_futures)} | 待下载{len(self.pending_ids)} | 已完成{len(self.completed_ids)}"
        )
    
    def _append_log(self, text: str, level: str = "info") -> None:
        """添加日志，支持级别和颜色
        
        Args:
            text: 日志内容
            level: 日志级别 (info, progress, warning, error, task, success)
        """
        self.log_text.config(state=tk.NORMAL)
        
        # 根据日志级别应用不同颜色标签
        if level in ["info", "progress", "warning", "error", "task", "success"]:
            self.log_text.insert(END, text + "\n", level)
        else:
            self.log_text.insert(END, text + "\n")
        
        # 自动滚动到末尾
        self.log_text.see(END)
        self.log_text.config(state=tk.DISABLED)
    
    def _poll_logs(self) -> None:
        try:
            while True:
                tag, value = self.log_queue.get_nowait()
                if tag == "__TASK_LOG__":
                    tid_str: str
                    msg: str
                    tid_str, msg = value
                    self._append_log(f"[task-{tid_str}] {msg}")
                elif tag == "__PROGRESS__":
                    progress_tid_str: str
                    downloaded: int
                    total: int | None
                    progress_tid_str, downloaded, total = value
                    tid_str = progress_tid_str
                    task = self.tasks.get(int(tid_str))
                    if task is not None:
                        task.downloaded_fragments = int(downloaded)
                        task.total_fragments = int(total) if total is not None else None
                        self._upsert_active_row(task)
                elif tag == "__TASK_DONE__":
                    self._handle_task_done(value)
                elif tag == "__ERROR__":
                    self._append_log(f"[error] {value}")
                    messagebox.showerror("执行失败", str(value))
        except queue.Empty:
            pass
        self.root.after(120, self._poll_logs)


def main() -> int:
    root = tk.Tk()
    
    # 创建应用（图标在 App.__init__ 中自动加载）
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
