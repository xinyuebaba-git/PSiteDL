# PSiteDL 应用图标

暗黑橙色风格的 PSiteDL 应用图标。

## 文件列表

- `icon-512.png` - 512x512 PNG (macOS icns 源文件)
- `icon-256.png` - 256x256 PNG
- `icon-32.png` - 32x32 PNG (用于 GUI 标题栏)
- `icon.icns` - macOS 图标格式

## 设计规范

### 配色方案
- **主色调**: 橙色 (#ff6b00)
- **背景**: 深色 (#1a1a1a)
- **文字**: 浅灰 (#e0e0e0)

### 设计元素
- 下载箭头 (橙色渐变)
- 视频播放按钮 (白色圆形 + 橙色三角形)
- 圆角矩形背景
- PSiteDL 文字标识 (大尺寸图标)

### 风格
- 现代简约
- 暗黑橙色主题
- 圆角设计

## 使用方法

图标已在 `site_gui.py` 中自动加载。启动 GUI 时会自动应用图标。

```bash
./run_psitedl_gui.sh
```

## 重新生成图标

如需修改图标设计，运行:

```bash
source .venv/bin/activate
python scripts/generate_icons.py
```
