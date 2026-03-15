# PSiteDL 批量下载功能实现总结

## 实现日期
2026-03-15

## 需求回顾
1. ✅ 命令行读取 URL 列表文件
2. ✅ 自动开始下载任务
3. ✅ 默认输出目录 ~/Downloads
4. ✅ 支持检测重复 URL

## 实现内容

### 1. URL 去重模块增强 (`src/webvidgrab/url_dedup.py`)

**新增功能:**
- `normalize_url()` - URL 标准化，移除跟踪参数 (utm_*, fbclid, gclid 等)
- `detect_duplicates()` - 检测 URL 列表中的重复项
- `generate_duplicate_report()` - 生成重复 URL 报告
- `format_duplicate_report()` - 格式化报告为文本
- `load_urls_from_file()` - 从文件加载 URL 列表
- `remove_duplicates()` - 移除重复 URL
- `DedupResult` - 去重结果数据类
- `DuplicateReport` - 重复报告数据类

**URL 标准化规则:**
- 统一 scheme 和 host 为小写
- 移除 path 末尾的斜杠
- 移除跟踪参数 (utm_*, fbclid, gclid, yclid, _hsenc, _hsmi, mc_cid, mc_eid)
- 排序 query parameters
- 移除 fragment

### 2. 批量下载模块修复 (`src/webvidgrab/batch_downloader.py`)

**修复的 Bug:**
- `config.config.profile` → `config.profile` (属性访问错误)
- `ConcurrentDownloader(concurrency=...)` → `ConcurrentDownloader(max_concurrent=...)` (参数名错误)
- `downloader.download()` → 使用 `run_site_download()` (方法不存在)

**功能:**
- 从 URL 列表文件批量下载
- 支持去重检测
- 并发下载 (默认 3 个)
- 进度显示
- 结果报告 (支持保存为 JSON)

### 3. CLI 集成 (`src/webvidgrab/site_cli.py`)

**新增参数:**
- `--url-file URL_FILE` - URL 列表文件路径
- `--output-dir OUTPUT_DIR` - 输出目录 (默认：~/Downloads)
- `--check-duplicates` - 启用重复检测 (默认开启)
- `--no-check-duplicates` - 禁用重复检测
- `--max-concurrent MAX_CONCURRENT` - 最大并发数 (默认：3)
- `--report-duplicates-only` - 仅报告重复，不下载

**工作模式:**
- 单 URL 模式：`site_cli.py <url>`
- 批量模式：`site_cli.py --url-file urls.txt`
- 去重报告模式：`site_cli.py --url-file urls.txt --report-duplicates-only`

## 使用示例

### 1. 检查 URL 文件中的重复项
```bash
cd /Users/yr001/.openclaw/workspace/PSiteDL
python3 -m src.webvidgrab.site_cli --url-file urls.txt --report-duplicates-only
```

### 2. 批量下载 (自动去重)
```bash
python3 -m src.webvidgrab.site_cli --url-file urls.txt --output-dir ~/Downloads
```

### 3. 批量下载 (禁用去重)
```bash
python3 -m src.webvidgrab.site_cli --url-file urls.txt --no-check-duplicates
```

### 4. 使用独立批量下载工具
```bash
python3 -m src.webvidgrab.batch_downloader --url-file urls.txt --check-duplicates --concurrency 5
```

## URL 列表文件格式

```text
# 这是注释
https://example.com/video1
https://example.com/video2
https://example.com/video3  # 行内注释也会被忽略
```

## 测试验证

### 测试 1: URL 标准化
```python
from src.webvidgrab.url_dedup import normalize_url

normalize_url("https://EXAMPLE.com/video/")  
# → "https://example.com/video"

normalize_url("https://example.com/video?utm_source=test")
# → "https://example.com/video"
```

### 测试 2: 重复检测
```bash
# 创建测试文件
cat > /tmp/test.txt << 'EOF'
https://example.com/video1
https://example.com/video2
https://example.com/video1  # 重复
https://example.com/video2?utm_source=test  # 标准化后重复
EOF

# 运行检测
python3 -m src.webvidgrab.site_cli --url-file /tmp/test.txt --report-duplicates-only
```

**输出:**
```
⚠ 检测到 2 组重复 URL:

1. https://example.com/video1
   域名：example.com
   出现位置：第 1, 3 行
   重复次数：2 次

2. https://example.com/video2
   域名：example.com
   出现位置：第 2, 4 行
   重复次数：2 次

原始 URL 数：4
唯一 URL 数：2
重复 URL 数：2
```

## 文件清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `src/webvidgrab/url_dedup.py` | ✅ 增强 | 新增去重函数和数据类 |
| `src/webvidgrab/batch_downloader.py` | ✅ 修复 | 修复 3 个 Bug |
| `src/webvidgrab/site_cli.py` | ✅ 增强 | 新增 5 个 CLI 参数 |

## 注意事项

1. **去重逻辑**: URL 去重在加载时自动执行，基于标准化后的 URL 进行比较
2. **并发限制**: 默认最大并发数为 3，可通过 `--max-concurrent` 调整
3. **输出目录**: 默认为 `~/Downloads`，可通过 `--output-dir` 覆盖
4. **日志**: 下载日志保存在 `logs/sitegrab/` 目录

## 后续改进建议

1. 添加下载历史记录，支持跨会话去重
2. 支持优先级队列，重要 URL 优先下载
3. 添加失败重试机制
4. 支持断点续传
5. 添加下载速度限制
