# PSiteDL 5 分钟快速入门

**适合人群**: 新手用户  
**预计时间**: 5 分钟  
**版本**: 0.4.0

---

## 🚀 快速开始

### 1. 安装 (2 分钟)

```bash
# 克隆项目
git clone https://github.com/xinyuebaba-git/PSiteDL.git
cd PSiteDL

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -U pip
pip install -e ".[dev]"
```

**验证安装**:
```bash
psitedl --version
# 输出：psitedl 0.4.0
```

---

### 2. 第一次下载 (1 分钟)

**单个视频下载**:
```bash
psitedl "https://example.com/video-page" \
  --output-dir "$HOME/Downloads"
```

**需要登录的网站** (使用浏览器 Cookie):
```bash
psitedl "https://example.com/video-page" \
  --output-dir "$HOME/Downloads" \
  --browser chrome \
  --profile Default
```

**查看实时进度**:
```
video.mp4: [████████████░░░░░░░] 65.5% | 2.5 MB/s | 剩余 12 秒
```

---

### 3. 批量下载 (1 分钟)

**创建 URL 文件** (`urls.txt`):
```
# 教程视频列表
https://example.com/tutorial/part1
https://example.com/tutorial/part2
https://example.com/tutorial/part3
```

**执行批量下载**:
```bash
psitedl --url-file "urls.txt" \
  --output-dir "$HOME/Downloads"
```

**并发下载** (大幅提升效率):
```bash
psitedl --url-file "urls.txt" \
  --output-dir "$HOME/Downloads" \
  --concurrency 5
```

---

### 4. 配置优化 (1 分钟)

**创建配置文件** (`~/.psitedl/config.json`):
```bash
mkdir -p ~/.psitedl
cat > ~/.psitedl/config.json << 'EOF'
{
  "output_dir": "~/Downloads",
  "browser": "chrome",
  "profile": "Default",
  "concurrency": 5,
  "max_retries": 3,
  "timeout": 30,
  "log_level": "INFO"
}
EOF
```

**使用配置文件**:
```bash
# 自动加载 ~/.psitedl/config.json
psitedl "https://example.com/video"

# 或指定自定义配置文件
psitedl "https://example.com/video" \
  --config /path/to/custom/config.json
```

---

## 📋 常用命令速查

### 基本下载
```bash
# 简单下载
psitedl "https://example.com/video"

# 指定输出目录
psitedl "https://example.com/video" --output-dir "/path/to/folder"

# 使用浏览器 Cookie
psitedl "https://example.com/video" --browser chrome
```

### 批量下载
```bash
# 批量下载
psitedl --url-file "urls.txt" --output-dir "$HOME/Downloads"

# 并发下载 (推荐)
psitedl --url-file "urls.txt" --concurrency 5

# 高并发模式
psitedl --url-file "urls.txt" --concurrency 10 --max-retries 5
```

### 带宽控制
```bash
# 限制带宽 (不影响其他网络使用)
psitedl --url-file "urls.txt" --bandwidth-limit 10

# 后台静默下载
psitedl --url-file "urls.txt" \
  --concurrency 2 \
  --bandwidth-limit 5 \
  --log-level WARNING
```

### 调试
```bash
# 查看详细日志
psitedl "url" --log-level DEBUG

# 查看帮助
psitedl --help
```

---

## 🎯 并发数建议

| 网络环境 | 推荐并发数 | 命令示例 |
|----------|------------|----------|
| 家庭宽带 (<100Mbps) | 2-3 | `--concurrency 3` |
| 百兆宽带 (100-500Mbps) | 3-5 | `--concurrency 5` |
| 千兆宽带 (>500Mbps) | 5-10 | `--concurrency 10` |
| 后台下载 (不影响工作) | 1-2 | `--concurrency 2 --bandwidth-limit 5` |

---

## ⚡ 效率技巧

### 1. 高并发下载 (千兆宽带)
```bash
psitedl --url-file "urls.txt" \
  --concurrency 10 \
  --max-retries 5 \
  --timeout 60
```

### 2. 后台静默下载 (不影响工作)
```bash
psitedl --url-file "urls.txt" \
  --concurrency 2 \
  --bandwidth-limit 5 \
  --log-level WARNING \
  --no-progress
```

### 3. 需要登录的网站
```bash
psitedl "https://example.com/video" \
  --browser chrome \
  --profile Default \
  --capture-seconds 30
```

### 4. 断点续传
```bash
# 第一次下载 (中断)
psitedl "https://example.com/large-video" --output-dir "$HOME/Downloads"

# 再次运行 (自动续传)
psitedl "https://example.com/large-video" --output-dir "$HOME/Downloads"
```

---

## ❓ 常见问题

### Q: 下载速度慢怎么办？
**A**: 增加并发数：
```bash
psitedl --url-file "urls.txt" --concurrency 5
```

### Q: 下载失败怎么办？
**A**: 
1. 查看详细日志：`psitedl "url" --log-level DEBUG`
2. 增加重试次数：`--max-retries 5`
3. 使用 Cookie：`--browser chrome`

### Q: 如何暂停下载？
**A**: 按 `Ctrl+C` 暂停。再次运行相同命令自动续传。

### Q: 下载的文件在哪里？
**A**: 默认在 `~/Downloads`。可通过 `--output-dir` 指定。

---

## 📖 下一步

完成快速入门后，你可以：

1. **查看详细文档**:
   - [下载使用指南](docs/DOWNLOADING.md) - 基本/批量/并发下载
   - [配置详解](docs/CONFIGURATION.md) - 配置项完整说明
   - [高级功能](docs/ADVANCED.md) - 并发/重试/带宽限制

2. **了解开发信息**:
   - [开发指南](DEVELOPMENT.md) - 开发者文档
   - [贡献指南](CONTRIBUTING.md) - 如何贡献
   - [变更日志](CHANGELOG.md) - 版本历史

3. **遇到问题？**:
   - [常见问题](README.md#常见问题)
   - [GitHub Issues](https://github.com/xinyuebaba-git/PSiteDL/issues)

---

## 🎉 开始使用

现在你已经掌握了 PSiteDL 的基本用法，开始下载你的第一个视频吧！

```bash
psitedl "https://example.com/your-first-video" --output-dir "$HOME/Downloads"
```

**祝你使用愉快！** 🚀

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
