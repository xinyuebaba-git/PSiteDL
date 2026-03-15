# PSiteDL 下载使用指南

本文档介绍如何使用 PSiteDL 进行视频下载，包括基本用法、批量下载和常见问题解决。

## 目录

- [基本下载](#基本下载)
- [批量下载](#批量下载)
- [并发下载](#并发下载)
- [带宽控制](#带宽控制)
- [断点续传](#断点续传)
- [常见问题](#常见问题)

---

## 基本下载

### 单个 URL 下载

最简单的下载方式：

```bash
psitedl "https://example.com/video-page" \
  --output-dir "$HOME/Downloads"
```

### 指定浏览器 Cookie

对于需要登录的网站，使用浏览器 Cookie：

```bash
psitedl "https://example.com/video-page" \
  --output-dir "$HOME/Downloads" \
  --browser chrome \
  --profile Default
```

支持的浏览器：
- `chrome` - Google Chrome
- `firefox` - Mozilla Firefox
- `edge` - Microsoft Edge
- `safari` - Apple Safari

### 自定义输出目录

```bash
psitedl "https://example.com/video" \
  --output-dir "/path/to/your/folder"
```

---

## 批量下载

### 使用 URL 文件

创建 URL 文件 (`urls.txt`)：

```
https://example.com/video1
https://example.com/video2
https://example.com/video3
```

执行批量下载：

```bash
psitedl --url-file "urls.txt" \
  --output-dir "$HOME/Downloads"
```

### URL 文件格式

- 每行一个 URL
- 支持注释 (以 `#` 开头)
- 空行自动跳过

示例：

```
# 教程视频列表
https://example.com/tutorial/part1
https://example.com/tutorial/part2

# 纪录片
https://example.com/documentary/nature
```

---

## 并发下载

### 什么是并发下载？

并发下载允许同时下载多个文件，大幅提升下载效率。

### 设置并发数

```bash
# 同时下载 5 个文件
psitedl --url-file "urls.txt" \
  --output-dir "$HOME/Downloads" \
  --concurrency 5
```

### 并发数建议

| 网络环境 | 推荐并发数 | 预计提升 |
|----------|------------|----------|
| 家庭宽带 (<100Mbps) | 2-3 | 2-3 倍 |
| 百兆宽带 (100-500Mbps) | 3-5 | 3-5 倍 |
| 千兆宽带 (>500Mbps) | 5-10 | 5-8 倍 |

### 高并发模式

适合带宽充足的场景：

```bash
psitedl --url-file "urls.txt" \
  --concurrency 10 \
  --max-retries 5 \
  --timeout 60
```

**注意**: 过高的并发数可能导致：
- 网络拥堵
- 服务器限流
- 下载失败率上升

---

## 带宽控制

### 为什么限制带宽？

- 避免占用全部网络资源
- 不影响其他网络使用 (视频通话、游戏等)
- 后台下载模式

### 设置带宽限制

```bash
# 限制为 10 Mbps
psitedl --url-file "urls.txt" \
  --bandwidth-limit 10
```

### 带宽限制场景

| 场景 | 推荐限制 | 说明 |
|------|----------|------|
| 后台下载 | 1-2 Mbps | 最小影响 |
| 工作时段 | 5-10 Mbps | 不影响办公 |
| 家庭共享 | 10-20 Mbps | 不影响家人 |
| 独享网络 | 无限制 | 全速下载 |

### 配置文件设置

在 `~/.psitedl/config.json` 中设置：

```json
{
  "concurrency": 5,
  "bandwidth_limit_mbps": 20
}
```

---

## 断点续传

### 自动续传

PSiteDL 支持断点续传功能。如果下载中断，再次运行相同命令会自动恢复：

```bash
# 第一次下载 (中断)
psitedl "https://example.com/large-video" \
  --output-dir "$HOME/Downloads"

# 再次运行 (自动续传)
psitedl "https://example.com/large-video" \
  --output-dir "$HOME/Downloads"
```

### 进度状态文件

下载进度保存在 `.download_state` 文件中，位于输出目录。

**注意**: 不要手动删除状态文件，否则将失去续传能力。

---

## 常见问题

### Q: 下载速度慢怎么办？

**A**: 尝试以下方法：

1. **增加并发数**:
   ```bash
   psitedl --url-file "urls.txt" --concurrency 5
   ```

2. **检查网络环境**: 确保没有其他程序占用带宽

3. **更换下载源**: 某些网站可能限速

### Q: 下载失败如何处理？

**A**: 

1. **查看详细日志**:
   ```bash
   psitedl "url" --log-level DEBUG
   ```

2. **增加重试次数**:
   ```bash
   psitedl --url-file "urls.txt" --max-retries 5
   ```

3. **使用 Cookie**: 某些网站需要登录
   ```bash
   psitedl "url" --browser chrome
   ```

4. **检查日志文件**: `~/.psitedl/psitedl.log`

### Q: 如何暂停下载？

**A**: 按 `Ctrl+C` 暂停下载。下次运行相同命令会自动续传。

### Q: 如何查看下载进度？

**A**: PSiteDL 默认显示实时进度：

```
video.mp4: [████████████░░░░░░░] 65.5% | 2.5 MB/s | 剩余 12 秒
```

批量下载显示整体进度：

```
整体进度：45.2% (9/20 文件)
```

### Q: 下载的文件在哪里？

**A**: 默认在 `~/Downloads` 目录。可通过 `--output-dir` 指定：

```bash
psitedl "url" --output-dir "/path/to/folder"
```

### Q: 如何限制磁盘使用？

**A**: 

1. 定期清理已下载文件
2. 使用 `--max-file-size` 限制单个文件大小
3. 监控输出目录磁盘空间

---

## 高级用法

### 组合示例

**高效批量下载** (适合千兆宽带):

```bash
psitedl --url-file "urls.txt" \
  --output-dir "$HOME/Downloads" \
  --concurrency 8 \
  --max-retries 5 \
  --timeout 60 \
  --log-level INFO
```

**后台静默下载** (不影响工作):

```bash
psitedl --url-file "urls.txt" \
  --output-dir "$HOME/Downloads" \
  --concurrency 2 \
  --bandwidth-limit 5 \
  --log-level WARNING \
  --no-progress
```

**需要登录的网站**:

```bash
psitedl "https://example.com/video" \
  --output-dir "$HOME/Downloads" \
  --browser chrome \
  --profile Default \
  --capture-seconds 30
```

---

## 相关文档

- [高级功能](ADVANCED.md) - 并发/重试/带宽详细说明
- [API 参考](API_REFERENCE.md) - 开发者 API 文档
- [配置详解](CONFIGURATION.md) - 配置项完整说明

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
