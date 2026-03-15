# 贡献指南

感谢你为 PSiteDL 项目做出贡献！

## 📋 目录

- [行为准则](#行为准则)
- [我能贡献什么](#我能贡献什么)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交指南](#提交指南)
- [测试要求](#测试要求)
- [Pull Request](#pull-request)

## 行为准则

- 尊重他人，保持友善
- 对事不对人，建设性讨论
- 欢迎新手，耐心指导
- 遵守开源精神，共享共赢

## 我能贡献什么

### 代码贡献
- 实现新功能 (参考 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md))
- 修复 Bug (查看 [Issues](https://github.com/xinyuebaba-git/PSiteDL/issues))
- 优化性能
- 改进错误处理

### 文档贡献
- 修正错别字/语法错误
- 补充缺失文档
- 改进示例代码
- 翻译文档

### 其他贡献
- 报告 Bug (提交 Issue)
- 提出功能建议
- 分享使用经验
- 推荐给朋友

## 开发流程

### 1. Fork 项目

```bash
# 在 GitHub 上点击 Fork 按钮
# 然后克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/PSiteDL.git
cd PSiteDL
```

### 2. 创建分支

```bash
# 保持 main 分支干净
git checkout main
git pull upstream main  # 同步上游

# 创建功能分支
git checkout -b feature/your-feature-name
# 或修复分支
git checkout -b fix/issue-123
```

### 3. 开发 (TDD 模式)

```bash
# 1. 先写测试
# 编辑 tests/test_your_feature.py

# 2. 运行测试 (应该失败)
pytest tests/test_your_feature.py -v

# 3. 实现功能
# 编辑 src/webvidgrab/your_feature.py

# 4. 再次运行测试 (应该通过)
pytest tests/test_your_feature.py -v

# 5. 确保所有测试通过
pytest tests/ -v
```

### 4. 代码质量检查

```bash
# 格式化代码
black src/ tests/

# 检查代码质量
ruff check src/ tests/

# 类型检查
mypy src/

# 运行测试并生成覆盖率报告
pytest --cov=src/webvidgrab --cov-report=term-missing
# 确保覆盖率 >= 80%
```

### 5. 提交代码

```bash
# 添加修改的文件
git add src/webvidgrab/your_feature.py
git add tests/test_your_feature.py

# 提交 (遵循提交规范)
git commit -m "feat: 添加 XXX 功能

- 实现 XXX 核心逻辑
- 添加单元测试
- 更新相关文档

Closes #123"

# 推送到远程
git push origin feature/your-feature-name
```

## 代码规范

### 类型注解

所有公共函数必须有类型注解：

```python
# ✅ 好的写法
def download_video(url: str, output_dir: Path) -> DownloadResult:
    ...

# ❌ 不好的写法
def download_video(url, output_dir):
    ...
```

### 文档字符串

使用 Google 风格：

```python
def process_video(url: str) -> bool:
    """处理视频下载
    
    Args:
        url: 视频页面 URL
        
    Returns:
        成功返回 True，失败返回 False
        
    Raises:
        DownloadError: 下载失败时抛出
    """
    ...
```

### 命名规范

```python
# 模块名：小写 + 下划线
site_cli.py  # ✅
SiteCli.py   # ❌

# 函数名：小写 + 下划线
load_config()  # ✅
loadConfig()   # ❌

# 类名：大驼峰
DownloadProgress  # ✅
downloadprogress  # ❌

# 常量：全大写 + 下划线
DEFAULT_TIMEOUT = 30  # ✅
defaultTimeout = 30   # ❌
```

## 提交指南

### 提交信息格式

遵循 [约定式提交](https://www.conventionalcommits.org/zh-hans/)：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式 (不影响代码运行)
- `refactor`: 重构 (既不是新功能也不是 Bug 修复)
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

### 示例

```bash
# 新功能
feat(config): 添加配置管理模块

- 实现 load_config 函数
- 实现 save_config 函数
- 添加单元测试

Closes #45

# Bug 修复
fix(downloader): 修复并发下载时的竞态条件

- 添加锁机制保护共享状态
- 增加并发测试用例

Fixes #67

# 文档更新
docs(readme): 补充安装说明

- 添加 Windows 安装步骤
- 更新依赖版本要求
```

## 测试要求

### 覆盖率要求

- **新增功能**: 覆盖率 >= 80%
- **核心模块**: 覆盖率 >= 90%
- **错误处理**: 分支覆盖率 100%

### 测试命名

```python
# 格式：test_<函数>_<场景>_<预期>
def test_load_config_from_file_success():  # ✅
    ...

def test_load_config_not_found_returns_default():  # ✅
    ...

def test_config():  # ❌ 太模糊
    ...
```

### Mock 外部依赖

```python
from unittest.mock import patch, Mock

@patch("webvidgrab.downloader.subprocess.run")
def test_download_with_mock(mock_run):
    mock_run.return_value = Mock(returncode=0)
    # 测试逻辑
```

## Pull Request

### PR 标题

```
feat: 添加配置管理功能
```

### PR 描述模板

```markdown
## 变更说明
- 实现 XXX 功能
- 修复 XXX 问题

## 测试
- [x] 单元测试通过
- [x] 代码覆盖率 >= 80%
- [x] 手动测试通过

## 截图 (如适用)
(添加截图或 GIF)

## 相关 Issue
Closes #123
```

### PR 检查清单

提交 PR 前确认：

- [ ] 代码通过所有测试
- [ ] 代码覆盖率符合要求
- [ ] 代码通过 Black/Ruff/Mypy 检查
- [ ] 添加了必要的文档字符串
- [ ] 更新了相关文档
- [ ] 提交信息符合规范
- [ ] PR 描述清晰

### 审查流程

1. **提交 PR**: 创建 Pull Request
2. **自动检查**: CI 运行测试和质量检查
3. **代码审查**: 维护者审查代码
4. **修改反馈**: 根据审查意见修改
5. **合并**: 审查通过后合并到 main 分支

## 常见问题

### Q: 如何同步上游代码？

```bash
git remote add upstream https://github.com/xinyuebaba-git/PSiteDL.git
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### Q: 如何撤销提交？

```bash
# 撤销最后一次提交 (保留修改)
git reset --soft HEAD~1

# 撤销提交并丢弃修改
git reset --hard HEAD~1
```

### Q: 如何合并多个提交？

```bash
# 交互式变基
git rebase -i HEAD~3
# 在编辑器中将 pick 改为 squash
```

## 联系方式

- **Issues**: https://github.com/xinyuebaba-git/PSiteDL/issues
- **讨论区**: (待添加)

---

**再次感谢你的贡献！** 🎉
