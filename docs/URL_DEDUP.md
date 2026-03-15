# PSiteDL URL 去重指南

本文档介绍如何清洗和去重 URL 文件，确保批量下载高效运行，避免重复下载。

## 目录

- [为什么需要去重](#为什么需要去重)
- [URL 去重方法](#url-去重方法)
- [URL 清洗技巧](#url-清洗技巧)
- [自动化脚本](#自动化脚本)
- [最佳实践](#最佳实践)

---

## 为什么需要去重

### 重复 URL 的问题

1. **浪费带宽和时间**: 同一视频下载多次
2. **占用磁盘空间**: 重复文件占用存储
3. **降低效率**: 增加不必要的下载任务
4. **混淆统计**: 影响下载进度和报告准确性

### 重复 URL 的常见场景

- 手动整理 URL 时不小心复制粘贴
- 从多个来源合并 URL 列表
- 多次运行脚本追加 URL 但未去重
- 网站 URL 参数不同但指向相同内容

示例:
```
https://example.com/video1
https://example.com/video2
https://example.com/video1  # 重复!
https://example.com/video3
https://example.com/video2  # 重复!
```

---

## URL 去重方法

### 方法 1: 使用 `sort -u` (推荐)

最简单快速的去重方法:

```bash
# 去重并排序
sort -u urls.txt > urls_deduped.txt

# 去重但不排序 (保持原顺序)
awk '!seen[$0]++' urls.txt > urls_deduped.txt
```

**说明**:
- `sort -u`: 排序并去重
- `awk '!seen[$0]++'`: 保持原始顺序去重

### 方法 2: 使用 Python 脚本

适合需要复杂逻辑的场景:

```python
#!/usr/bin/env python3
"""URL 去重脚本 - 保持原始顺序"""

def deduplicate_urls(input_file, output_file):
    seen = set()
    unique_urls = []
    
    with open(input_file, 'r') as f:
        for line in f:
            url = line.strip()
            # 跳过空行和注释
            if not url or url.startswith('#'):
                unique_urls.append(line)
                continue
            # 去重
            if url not in seen:
                seen.add(url)
                unique_urls.append(line)
    
    with open(output_file, 'w') as f:
        f.writelines(unique_urls)
    
    print(f"原始 URL 数：{len(unique_urls) + len(seen)}")
    print(f"去重后 URL 数：{len(seen)}")
    print(f"移除重复：{len(unique_urls) + len(seen) - len(seen)}")

if __name__ == '__main__':
    deduplicate_urls('urls.txt', 'urls_clean.txt')
```

使用:
```bash
python3 dedup_urls.py
```

### 方法 3: 使用 PSiteDL 内置功能 (如果支持)

某些版本的 PSiteDL 可能内置去重功能:

```bash
# 检查是否支持自动去重
psitedl --url-file "urls.txt" --dedup
```

---

## URL 清洗技巧

### 1. 移除空行

```bash
# 移除空行
grep -v '^$' urls.txt > urls_no_empty.txt

# 或使用 sed
sed '/^$/d' urls.txt > urls_no_empty.txt
```

### 2. 移除注释

```bash
# 移除注释行
grep -v '^#' urls.txt > urls_no_comments.txt
```

### 3. 移除首尾空白

```bash
# 使用 sed 移除每行首尾空白
sed 's/^[[:space:]]*//;s/[[:space:]]*$//' urls.txt > urls_trimmed.txt
```

### 4. 标准化 URL

统一 URL 格式 (移除末尾斜杠、统一协议等):

```bash
# 移除末尾斜杠
sed 's/\/$//' urls.txt > urls_normalized.txt

# 统一为 https
sed 's/^http:\/\//https:\/\//g' urls.txt > urls_https.txt
```

### 5. 完整清洗流程

组合多个步骤:

```bash
# 完整清洗：移除空行 + 移除注释 + 去重
cat urls.txt | \
  grep -v '^$' | \
  grep -v '^#' | \
  sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | \
  awk '!seen[$0]++' > urls_clean.txt
```

---

## 自动化脚本

### 脚本 1: 一键清洗脚本

创建 `clean_urls.sh`:

```bash
#!/bin/bash
# URL 清洗脚本

INPUT_FILE="${1:-urls.txt}"
OUTPUT_FILE="${2:-urls_clean.txt}"

echo "清洗 URL 文件：$INPUT_FILE -> $OUTPUT_FILE"

# 统计原始数据
ORIGINAL_COUNT=$(wc -l < "$INPUT_FILE")
echo "原始行数：$ORIGINAL_COUNT"

# 清洗：移除空行、注释、空白，去重
cat "$INPUT_FILE" | \
  grep -v '^[[:space:]]*$' | \
  grep -v '^[[:space:]]*#' | \
  sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | \
  awk '!seen[$0]++' > "$OUTPUT_FILE"

# 统计清洗后数据
CLEAN_COUNT=$(wc -l < "$OUTPUT_FILE")
echo "清洗后行数：$CLEAN_COUNT"
echo "移除重复/无效：$((ORIGINAL_COUNT - CLEAN_COUNT))"

echo "✓ 清洗完成：$OUTPUT_FILE"
```

使用:
```bash
chmod +x clean_urls.sh
./clean_urls.sh urls.txt
```

### 脚本 2: Python 高级清洗脚本

创建 `clean_urls_advanced.py`:

```python
#!/usr/bin/env python3
"""
URL 高级清洗脚本
功能：去重、标准化、验证格式
"""

import re
from urllib.parse import urlparse

def is_valid_url(url):
    """检查 URL 格式是否有效"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def normalize_url(url):
    """标准化 URL"""
    # 移除末尾斜杠
    url = url.rstrip('/')
    # 统一为小写 (域名部分)
    parsed = urlparse(url)
    normalized = parsed._replace(netloc=parsed.netloc.lower())
    return normalized.geturl()

def clean_urls(input_file, output_file, validate=False):
    """清洗 URL 文件"""
    seen = set()
    valid_urls = []
    invalid_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            original_line = line
            url = line.strip()
            
            # 保留注释和空行
            if not url or url.startswith('#'):
                valid_urls.append(original_line)
                continue
            
            # 标准化 URL
            url = normalize_url(url)
            
            # 验证 URL (可选)
            if validate and not is_valid_url(url):
                print(f"警告：第{line_num}行 URL 格式无效：{url}")
                invalid_count += 1
                continue
            
            # 去重
            if url not in seen:
                seen.add(url)
                valid_urls.append(url + '\n')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(valid_urls)
    
    # 打印统计
    total_lines = len(valid_urls) + invalid_count
    unique_urls = len(seen)
    print(f"\n清洗统计:")
    print(f"  原始行数：{total_lines}")
    print(f"  有效 URL: {unique_urls}")
    print(f"  重复/无效：{total_lines - unique_urls}")
    if validate:
        print(f"  格式无效：{invalid_count}")
    print(f"\n✓ 输出文件：{output_file}")

if __name__ == '__main__':
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'urls.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'urls_clean.txt'
    validate = '--validate' in sys.argv
    
    clean_urls(input_file, output_file, validate=validate)
```

使用:
```bash
# 基本清洗
python3 clean_urls_advanced.py urls.txt

# 带 URL 格式验证
python3 clean_urls_advanced.py urls.txt urls_clean.txt --validate
```

---

## 最佳实践

### 1. 定期清洗 URL 文件

在批量下载前始终清洗 URL 文件:

```bash
# 下载前清洗
./clean_urls.sh urls.txt urls_clean.txt
psitedl --url-file "urls_clean.txt" --output-dir "~/Downloads"
```

### 2. 维护主 URL 清单

保持一个主 URL 文件，每次新增时清洗:

```bash
# 追加新 URL
cat new_urls.txt >> master_urls.txt

# 清洗主清单
./clean_urls.sh master_urls.txt master_urls_clean.txt

# 使用清洗后的文件
psitedl --url-file "master_urls_clean.txt"
```

### 3. 使用版本控制

对 URL 文件使用 Git 管理:

```bash
# 初始化 Git
git init
git add urls.txt

# 每次修改后提交
git commit -m "Add new video URLs"

# 查看变更
git diff urls.txt
```

### 4. 分类管理 URL

按类别组织 URL 文件:

```
urls/
├── tutorials.txt      # 教程视频
├── documentaries.txt  # 纪录片
├── lectures.txt       # 讲座
└── entertainment.txt  # 娱乐视频
```

分别清洗每个文件:
```bash
for file in urls/*.txt; do
  ./clean_urls.sh "$file" "urls/clean_$(basename $file)"
done
```

### 5. 检查 URL 有效性

下载前快速检查 URL 是否可访问:

```bash
#!/bin/bash
# 检查 URL 可访问性

while IFS= read -r url; do
  [[ -z "$url" || "$url" =~ ^# ]] && continue
  
  status=$(curl -o /dev/null -s -w "%{http_code}" "$url")
  if [ "$status" -eq 200 ]; then
    echo "✓ $url"
  else
    echo "✗ $url (HTTP $status)"
  fi
done < urls.txt
```

---

## 常见问题

### Q: 去重后顺序变了怎么办？

使用 `awk` 保持原始顺序:
```bash
awk '!seen[$0]++' urls.txt > urls_deduped.txt
```

### Q: 如何识别相似但不完全相同的 URL？

某些 URL 可能只有参数不同但内容相同:

```python
# 移除查询参数后比较
from urllib.parse import urlparse, parse_qs

url1 = "https://example.com/video?id=123&ref=abc"
url2 = "https://example.com/video?id=123&ref=xyz"

parsed1 = urlparse(url1)
parsed2 = urlparse(url2)

# 比较基础 URL (不含参数)
base1 = f"{parsed1.scheme}://{parsed1.netloc}{parsed1.path}"
base2 = f"{parsed2.scheme}://{parsed2.netloc}{parsed2.path}"

print(base1 == base2)  # True - 相同视频
```

### Q: 如何合并多个 URL 文件并去重？

```bash
# 合并并去重
cat urls1.txt urls2.txt urls3.txt | \
  awk '!seen[$0]++' > merged_urls.txt
```

### Q: 去重后如何知道移除了哪些重复项？

```bash
# 显示重复项
sort urls.txt | uniq -d > duplicates.txt
cat duplicates.txt
```

---

## 相关文档

- [批量下载指南](BATCH_DOWNLOAD.md) - 批量下载完整指南
- [下载使用指南](DOWNLOADING.md) - 基本下载操作
- [高级功能](ADVANCED.md) - 并发/重试机制

---

**最后更新**: 2026-03-15  
**版本**: 0.4.0
