# 桂林理工大学教务处通知爬虫

这是一个自动化爬取桂林理工大学教务处通知公告的项目，提供高级内容处理、归档和RSS订阅功能。

## 功能特性

- 自动爬取教务处通知公告页面的最新文章
- 提取文章标题、链接和发布日期
- 按日期以JSON格式缓存文章
- 网络失败时提供缓存加载的备用方案
- **智能标记**：自动标记包含关键词的重要文章
- **完整文章下载**：将完整文章内容下载为Markdown文件
- **附件处理**：自动下载PDF/DOCX等附件到文章文件夹
- **归档管理**：自动清理和归档旧文章
- **增强RSS生成**：使用本地Markdown内容创建RSS/Atom订阅源
- **本地RSS服务器**：内置Web服务器，支持自动端口切换

## 重要文章关键词

包含以下关键词的文章会被自动标记为重要：
- 注意事项
- 选课
- 公告
- 毕业论文
- 课表
- 考试
- 开课信息
- 学位证书
- 毕业
- 报名
- 证书
- 缓考
- 重修
- 答辩
- 实习
- 停开

## 核心增强功能

### RSS内容特性
- ✅ 显示**所有重要文章**
- ✅ 使用**本地Markdown内容**作为文章正文
- ✅ 当Markdown内容不可用时回退到基本元数据
- ✅ 包含原文链接以获取完整信息
- ✅ 正确的内容清理和格式化
- ✅ 自动识别并显示PDF附件链接

### 服务器特性
- ✅ **自动端口切换**：当4590端口被占用时自动查找可用端口
- ✅ **优雅错误处理**：清晰的错误消息和恢复选项
- ✅ **交互式菜单**：易于使用的命令行界面
- ✅ **健康监控**：服务监控的状态端点

## 安装

1. 克隆此仓库
2. 安装所需依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. RSS服务测试（可选）：
   ```bash
   pip install requests
   ```

## GitHub Actions 自动化

本项目配置为在GitHub Actions上每周四自动运行：

- **定时任务**：每周四 UTC 00:00（北京时间 08:00）
- **工作流文件**：`.github/workflows/weekly-update.yml`
- **执行操作**：
  1. 运行爬虫获取最新文章
  2. 下载重要文章和附件
  3. 生成包含更新内容的RSS订阅源
  4. 提交并推送更改回仓库

### 手动触发

你也可以从GitHub手动触发工作流：
1. 进入仓库的 "Actions" 标签页
2. 选择 "Weekly RSS Update" 工作流
3. 点击 "Run workflow" 按钮

### 推送触发

每次向 `main` 或 `master` 分支推送代码时，工作流也会自动运行。

### GitHub Pages RSS订阅地址

如果启用GitHub Pages，你的RSS订阅源将在以下地址可用：
- **RSS 2.0**：`https://yourusername.github.io/glut_rss/rss/rss.xml`
- **Atom**：`https://yourusername.github.io/glut_rss/rss/atom.xml`

将 `yourusername` 替换为你的实际GitHub用户名。

## 使用方法

### 主爬虫程序
```bash
python glut_news_scraper.py
```

### 归档管理工具
```bash
python archive_manager.py
```

### RSS服务
```bash
python local_rss_server.py
```

### RSS生成器（独立运行）
```bash
python rss_generator.py
```

## 目录结构

```
.
├── cache/                    # 按日期组织的JSON缓存文件（近期文章）
│   ├── 2026-01-20.json
│   └── ...
├── articles/                 # 完整文章内容和附件
│   ├── 文章标题1/
│   │   ├── 文章标题1.md          # Markdown格式的文章内容
│   │   └── attachment.pdf       # 下载的附件
│   └── ...
├── archive/                  # 按期间组织的归档文章
│   ├── 2024年上半年/              # 2024年上半年
│   │   └── 2024年上半年_articles.json
│   └── ...
├── rss/                      # 生成的RSS订阅源文件
│   ├── rss.xml               # RSS 2.0格式（仅重要文章）
│   └── atom.xml              # Atom格式（仅重要文章）
├── glut_news_scraper.py      # 主爬虫脚本
├── archive_manager.py        # 归档管理工具
├── rss_generator.py          # RSS订阅源生成器
└── local_rss_server.py       # 本地RSS Web服务器
```

## RSS服务端点

运行本地RSS服务器（`python local_rss_server.py`）时：

- **RSS 2.0 订阅源**：`http://127.0.0.1:4590/rss.xml`（或自动切换的端口）
- **Atom 订阅源**：`http://127.0.0.1:4590/atom.xml`（或自动切换的端口）
- **API文章列表**：`http://127.0.0.1:4590/api/articles`（JSON格式）
- **服务状态**：`http://127.0.0.1:4590/status`

**注意**：
- RSS订阅源仅包含标记为重要的文章（包含指定关键词）
- 显示所有重要文章（不限制数量）
- 如果4590端口被占用，服务器会自动切换到可用端口

## 归档管理功能

`archive_manager.py` 提供：

1. **缓存统计**：查看缓存文章的详细统计信息
2. **自动清理**：删除6个月以前的缓存文件
3. **智能归档**：将旧文章归档到年度/半年度目录
4. **完整工作流**：组合清理和归档流程

### 归档组织方式

旧文章会自动组织到以下目录：
- `2024年上半年`（2024年上半年：1-6月）
- `2024年下半年`（2024年下半年：7-12月）
- `2025年上半年`（2025年上半年：1-6月）
- 以此类推...

## 缓存结构

文章在 `cache/` 目录中按日期缓存，每天一个文件：
- 每个文件以日期格式命名：`YYYY-MM-DD.json`
- 文件包含该日期文章的JSON数组
- 每篇文章包含：标题、链接、日期、抓取时间戳和重要性标记

## 文章处理流程

重要文章会自动：
1. 在列表中用 ⭐ 标记
2. 下载为包含完整内容的Markdown文件
3. 自动下载附件（PDF、DOCX等）
4. 存储在以文章标题命名的独立文件夹中
5. 包含在RSS订阅源中，使用本地内容供订阅

## RSS内容说明

RSS订阅源中的文章内容根据以下规则显示：

1. **有Markdown正文**：显示完整的文章正文内容
2. **有PDF附件**：在正文后显示PDF附件链接（指向原文）
3. **无正文但有PDF**：只显示PDF附件链接
4. **无正文也无PDF**：只显示原文链接

## 故障排除

### 端口冲突
如果遇到 "Address already in use" 错误：
- 服务器会自动查找并切换到可用端口
- 检查控制台输出以获取实际使用的端口
- 相应更新RSS阅读器订阅URL

### Python版本问题
对于Python版本问题：
1. 确保你有 Python 3.6+
2. 安装所需包：`pip install -r requirements.txt`

### RSS服务问题
对于RSS服务问题：
1. 检查服务器是否正在运行
2. 验证 `rss/` 目录中是否生成了RSS文件
3. 确认缓存文件中存在重要文章
4. 确保 `articles/` 目录中存在对应的Markdown文件
5. 如果从外部网络访问，检查防火墙设置

### GitHub Actions权限问题
如果GitHub Actions运行失败：
1. 进入仓库的 Settings > Actions > General
2. 找到 Workflow permissions 部分
3. 选择 "Read and write permissions"
4. 点击 Save 保存

## 项目文件说明

- **glut_news_scraper.py**：主爬虫程序，负责从教务处网站抓取文章
- **rss_generator.py**：RSS订阅源生成器，生成RSS 2.0和Atom格式
- **archive_manager.py**：归档管理工具，提供缓存清理和文章归档功能
- **local_rss_server.py**：本地RSS服务器，提供Web访问RSS订阅源

## 技术栈

- Python 3.6+
- requests：HTTP请求
- BeautifulSoup4：HTML解析
- xml.etree.ElementTree：XML生成

## 许可证

本项目仅供学习和个人使用。

## 贡献

欢迎提交问题和拉取请求。

## 更新日志

### v2.0
- 添加GitHub Actions自动化
- 每周四自动更新RSS
- 推送代码时自动运行
- 支持手动触发工作流
- 优化RSS内容显示逻辑
- 添加favicon支持
- 显示所有重要文章（不限制数量）

### v1.0
- 初始版本
- 基本爬虫功能
- RSS订阅源生成
- 本地服务器
