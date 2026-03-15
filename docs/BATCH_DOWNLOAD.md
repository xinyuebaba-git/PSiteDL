# PSiteDL 批量下载指南

本文档详细介绍如何使用 PSiteDL 进行批量视频下载，包括 URL 文件格式、并发控制、错误处理等高级功能。

## 目录

- [快速开始](#快速开始)
- [URL 文件格式](#url-文件格式)
- [并发控制](#并发控制)
- [错误处理与重试](#错误处理与重试)
- [带宽管理](#带宽管理)
- [进度监控](#进度监控)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

---

## 快速开始

### 基本批量下载

1. **创建 URL 文件** (`urls.txt`):
   ```
   https://example.com/video1
   https://example.com/video2
   https://example.com/video3
   ```

2. **执行批量下载**:
   ```bash
   psitedl --url-file "urls.txt" \
     --output-dir "$HOME/Downloads"
   ```

### 使用示例文件

PSiteDL 提供示例 URL 文件供测试:

```bash
# 复制示例文件
cp examples/urls_sample.txt ./my_urls.txt

# 编辑示例文件 (替换为真实 URL)
nano my_urls.txt

# 执行下载
psitedl --url-file "my_urls.txt" --output-dir "./downloads"
```

---

## URL 文件格式

### 基本格式

- **每行一个 URL**
- **支持空行** (自动跳过)
- **支持注释** (以 `#` 开头)

示例:
```
# 教程系列
https://example.com/tutorial/intro
https://example.com/tutorial/part1
https://example.com/tutorial/part2

# 纪录片
https://example.com/docs/nature
https://example.com/docs/technology
```

### 高级格式

#### 1. 带注释的分类

```
# ========== 第一部分：基础教程 ==========
https://example.com/basics/01-intro
https://example.com/basics/02-setup

# ========== 第二部分：进阶内容 ==========
https://example.com/advanced/01-deep-dive
https://example.com/advanced/02-optimization
```

#### 2. 带优先级的 URL (通过顺序控制)

URL 文件中的顺序即为下载优先级，排在前面的 URL 优先下载:

```
# 紧急任务 (优先下载)
https://example.com/urgent/video1
https://example.com/urgent/video2

# 普通任务
https://example.com/normal/video3
https://example.com/normal/video4
```

#### 3. 带元数据的 URL (通过注释)

```
# title: 入门教程 | duration: 15min | size: ~500MB
https://example.com/tutorial/intro

# title: 进阶指南 | duration: 30min | size: ~1GB
https://example.com/tutorial/advanced
```

**注意**: 元数据仅供人工阅读，PSiteDL 当前不解析元数据注释。

---

## 并发控制

### 什么是并发下载？

并发下载允许同时下载多个文件，大幅提升整体下载效率。

### 设置并发数

```bash
# 同时下载 3 个文件 (默认)
psitedl --url-file "urls.txt" --concurrency 3

# 高并发模式 (适合千兆宽带)
psitedl --url-file "urls.txt" --concurrency 10
```

### 并发数选择指南

| 网络环境 | 带宽 | 推荐并发数 | 预计效率提升 |
|----------|------|------------|--------------|
| 家庭宽带 | <100 Mbps | 2-3 | 2-3 倍 |
| 百兆宽带 | 100-500 Mbps | 3-5 | 3-5 倍 |
| 千兆宽带 | 500-1000 Mbps | 5-8 | 5-8 倍 |
| 企业网络 | >1000 Mbps | 8-10 | 8-10 倍 |

### 并发数过高可能导致的问题

- ⚠️ 网络拥堵，实际速度下降
- ⚠️ 服务器限流或封禁
- ⚠️ 下载失败率上升
- ⚠️ 系统资源 (CPU/内存) 占用过高

### 动态调整并发数

根据实时下载情况调整:

```bash
# 初始低并发测试
psitedl --url-file "urls.txt" --concurrency 3

# 如果速度慢且带宽充足，增加并发
psitedl --url-file "urls.txt" --concurrency 8

# 如果失败率高，降低并发
psitedl --url-file "urls.txt" --concurrency 2
```

---

## 错误处理与重试

### 自动重试机制

PSiteDL 自动重试失败的下载任务:

```bash
# 默认重试 3 次
psitedl --url-file "urls.txt"

# 自定义重试次数
psitedl --url-file "urls.txt" --max-retries 5
```

### 重试策略

- **网络错误**: 自动重试 (超时、连接重置、DNS 失败)
- **服务器错误** (5xx): 自动重试
- **客户端错误** (4xx): 不重试 (需要人工介入)
- **本地错误** (磁盘满、权限不足): 不重试

### 查看失败任务

下载完成后，查看失败的任务列表:

```bash
# 查看日志中的错误
grep "ERROR" ~/.psitedl/psitedl.log

# 查看失败报告 (如果有)
cat output_dir/failed_urls.txt
```

### 重新下载失败的 URL

从失败 URL 创建新的 URL 文件:

```bash
# 提取失败的 URL
grep "FAILED" ~/.psitedl/psitedl.log | \
  awk '{print $NF}' > failed_urls.txt

# 重新下载 (增加重试次数)
psitedl --url-file "failed_urls.txt" \
  --max-retries 10 \
  --log-level DEBUG
```

---

## 带宽管理

### 为什么限制带宽？

- 避免占用全部网络资源
- 不影响其他网络使用 (视频会议、在线游戏等)
- 后台静默下载
- 共享网络环境下的公平使用

### 设置带宽限制

```bash
# 限制为 10 Mbps
psitedl --url-file "urls.txt" --bandwidth-limit 10

# 限制为 50 Mbps (适合千兆宽带)
psitedl --url-file "urls.txt" --bandwidth-limit 50
```

### 带宽限制场景

| 场景 | 推荐限制 | 说明 |
|------|----------|------|
| 后台下载 | 1-2 Mbps | 最小化影响 |
| 工作时段 | 5-10 Mbps | 不影响办公网络 |
| 家庭共享 | 10-20 Mbps | 不影响家人使用 |
| 夜间下载 | 无限制 | 充分利用带宽 |
| 独享网络 | 无限制 | 全速下载 |

### 带宽限制与并发配合

```bash
# 高并发 + 带宽限制 (充分利用但不过载)
psitedl --url-file "urls.txt" \
  --concurrency 8 \
  --bandwidth-limit 50
```

---

## 进度监控

### 实时进度显示

批量下载时显示整体进度:

```
整体进度：45.2% (9/20 文件)
当前下载：video_15.mp4 [████████████░░░░░░░] 65.5% | 2.5 MB/s
已完成：8 文件 | 失败：0 文件 | 进行中：1 文件
```

### 静默模式

后台运行时不显示进度:

```bash
psitedl --url-file "urls.txt" \
  --no-progress \
  --log-level WARNING
```

### 日志查看

```bash
# 实时查看日志
tail -f ~/.psitedl/psitedl.log

# 查看已完成的下载
grep "completed" ~/.psitedl/psitedl.log

# 查看下载统计
grep "Summary" ~/.psitedl/psitedl.log
```

---

## 最佳实践

### 1. 大规模批量下载 (100+ URL)

```bash
# 分批处理 (每批 50 个 URL)
head -50 urls.txt > batch1.txt
psitedl --url-file "batch1.txt" --concurrency 5

tail -n +51 urls.txt | head -50 > batch2.txt
psitedl --url-file "batch2.txt" --concurrency 5
```

### 2. 夜间无人值守下载

```bash
# 高并发 + 无带宽限制 + 详细日志
psitedl --url-file "urls.txt" \
  --concurrency 10 \
  --max-retries 5 \
  --log-level INFO \
  --log-file "night_download.log"
```

### 3. 重要任务优先

```bash
# 创建优先级 URL 文件
cat > priority_urls.txt << EOF
# 高优先级 (先下载)
https://example.com/important/video1
https://example.com/important/video2

# 普通优先级
https://example.com/normal/video3
EOF

# 使用低并发确保重要任务快速完成
psitedl --url-file "priority_urls.txt" \
  --concurrency 2 \
  --max-retries 10
```

### 4. 带宽敏感环境

```bash
# 限制带宽 + 低并发 + 后台模式
psitedl --url-file "urls.txt" \
  --concurrency 2 \
  --bandwidth-limit 5 \
  --no-progress \
  --log-level WARNING
```

### 5. 不稳定网络环境

```bash
# 高重试次数 + 长超时 + 低并发
psitedl --url-file "urls.txt" \
  --concurrency 2 \
  --max-retries 10 \
  --timeout 120
```

---

## 故障排除

### Q: 批量下载中途停止

**可能原因**:
- 网络中断
- 系统休眠
- 磁盘空间不足

**解决方案**:
```bash
# 1. 检查磁盘空间
df -h ~/Downloads

# 2. 检查网络连接
ping -c 3 example.com

# 3. 防止系统休眠 (macOS)
caffeinate -s

# 4. 重新运行 (自动续传)
psitedl --url-file "urls.txt" --output-dir "~/Downloads"
```

### Q: 部分 URL 下载失败

**可能原因**:
- URL 失效
- 网站限流
- 需要登录

**解决方案**:
```bash
# 1. 检查失败的 URL
grep "ERROR" ~/.psitedl/psitedl.log

# 2. 手动测试 URL
curl -I "https://example.com/failed-url"

# 3. 使用 Cookie 重试
psitedl --url-file "failed_urls.txt" \
  --browser chrome \
  --max-retries 5
```

### Q: 下载速度过慢

**解决方案**:
```bash
# 1. 增加并发数
psitedl --url-file "urls.txt" --concurrency 10

# 2. 移除带宽限制
psitedl --url-file "urls.txt" --bandwidth-limit 0

# 3. 检查网络速度
speedtest-cli

# 4. 更换网络环境
```

### Q: 如何监控批量下载进度？

**方案 1**: 使用日志
```bash
# 实时查看进度
tail -f ~/.psitedl/psitedl.log | grep -E "(completed|failed|progress)"
```

**方案 2**: 使用 `watch` 命令
```bash
# 每 5 秒刷新一次进度
watch -n 5 'psitedl --url-file "urls.txt" --dry-run'
```

**方案 3**: 检查输出目录
```bash
# 查看已下载文件数量
ls -1 ~/Downloads/*.mp4 | wc -l
```

---

## 相关文档

- [URL 去重说明](URL_DEDUP.md) - URL 去重和清洗指南
- [下载使用指南](DOWNLOADING.md) - 基本下载操作
- [高级功能](ADVANCED.md) - 并发架构/重试机制详解
- [配置详解](CONFIGURATION.md) - 配置项完整说明

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
