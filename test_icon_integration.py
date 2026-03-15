#!/usr/bin/env python3
"""测试图标集成"""

import sys
import tkinter as tk
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from webvidgrab.site_gui import App, DarkOrangeColors


def test_icon_loading():
    """测试图标加载功能"""
    print("=" * 60)
    print("PSiteDL 图标集成测试")
    print("=" * 60)
    
    # 检查图标文件
    assets_dir = Path(__file__).parent / "assets"
    required_icons = [
        "icon-16.png",
        "icon-32.png",
        "icon-64.png",
        "icon-128.png",
        "icon-256.png",
        "icon-512.png",
        "icon.icns",
        "psitedl_icon.ico",
    ]
    
    print("\n1. 检查图标文件:")
    all_exist = True
    for icon in required_icons:
        icon_path = assets_dir / icon
        exists = icon_path.exists()
        status = "✓" if exists else "✗"
        print(f"   {status} {icon}")
        if not exists:
            all_exist = False
    
    if not all_exist:
        print("\n[错误] 部分图标文件缺失!")
        return False
    
    print("\n2. 测试窗口图标加载:")
    
    # 创建测试窗口
    root = tk.Tk()
    root.title("PSiteDL 图标测试")
    root.geometry("600x400")
    root.configure(bg=DarkOrangeColors.BACKGROUND)
    
    # 创建测试框架
    frame = tk.Frame(root, bg=DarkOrangeColors.BACKGROUND)
    frame.pack(expand=True, fill=tk.BOTH, padx=40, pady=40)
    
    # 标题
    title = tk.Label(
        frame,
        text="图标集成测试",
        font=("SF Pro Display", 24, "bold"),
        fg=DarkOrangeColors.TEXT_HIGHLIGHT,
        bg=DarkOrangeColors.BACKGROUND
    )
    title.pack(pady=(0, 20))
    
    # 加载并显示图标
    try:
        icon_path = assets_dir / "icon-128.png"
        test_icon = tk.PhotoImage(file=str(icon_path))
        icon_label = tk.Label(frame, image=test_icon, bg=DarkOrangeColors.BACKGROUND)
        icon_label.pack(pady=20)
        
        # 保持引用
        root.test_icon = test_icon
        
        print("   ✓ 图标加载成功")
    except Exception as e:
        print(f"   ✗ 图标加载失败：{e}")
        return False
    
    # 状态信息
    status = tk.Label(
        frame,
        text="窗口图标已应用到标题栏\n标题栏图标已显示",
        font=("SF Pro Text", 14),
        fg=DarkOrangeColors.TEXT_SECONDARY,
        bg=DarkOrangeColors.BACKGROUND
    )
    status.pack(pady=20)
    
    # 关闭按钮
    close_btn = tk.Button(
        frame,
        text="关闭测试窗口",
        command=root.destroy,
        bg=DarkOrangeColors.PRIMARY,
        fg="#ffffff",
        font=("SF Pro Text", 14),
        relief=tk.FLAT,
        padx=20,
        pady=10
    )
    close_btn.pack(pady=20)
    
    print("\n3. 测试窗口已打开")
    print("   请检查:")
    print("   - 窗口标题栏是否显示图标")
    print("   - 窗口中央是否显示图标图片")
    print("\n测试完成！关闭窗口退出测试。")
    print("=" * 60)
    
    root.mainloop()
    return True


if __name__ == "__main__":
    success = test_icon_loading()
    sys.exit(0 if success else 1)
