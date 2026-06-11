# 会话上下文保存

## 项目信息
- **项目名称**: 闵行区华漕社区MHP0-1401单元28-01地块综合开发项目
- **项目ID**: 3013787
- **招标ID**: 3002648
- **数据来源**: 上海市公共资源交易中心 (https://ciac.zjw.sh.gov.cn)

## 已完成的工作

### 1. 爬虫脚本 (scrape_all_announcements.py)
- 使用 Playwright + httpx 抓取项目全生命周期公告
- 5个公告类型：招标计划、招标公告、补充公告、中标候选人公示、中标结果公告
- 技术：网络拦截捕获 PDF 下载请求，绕过登录墙

### 2. PDF 解析脚本 (parse_candidate_pdf.py)
- 使用 pdfplumber 解析中标候选人公示 PDF
- 提取表格数据并转换为 Markdown 格式
- 核心数据：9个投标人报价明细、评标委员会得分、技术标评审结果

### 3. MCP 配置 (camoufox-reverse)
- 仓库位置: D:/PythonProject/camoufox-reverse-mcp
- Conda 环境: mcp (Python 3.10.20)
- Python 路径: D:/anaconda/envs/mcp/python
- 配置文件: C:/Users/Ran'lenovo/.claude.json
- MCP 状态: ✅ 已连接 (camoufox-reverse: ✓ Connected)
- 可用工具: 35 个逆向分析工具

### 4. Skill 安装 (hello_js_reverse_skill)
- 安装位置: ~/.claude/skills/hello_js_reverse_skill/
- 状态: ✅ 已安装
- Node.js 包: crypto-js, axios, node-forge, jsdom (已安装)
- Python 包: requests, pycryptodome, httpx, curl_cffi (已安装)

## 生成的文件
```
闵行区华漕社区MHP0-1401单元28-01地块综合开发项目/
├── 招标计划.md
├── 招标公告.md
├── 补充公告.md
├── 中标候选人公示.md
├── 中标候选人公示.pdf
└── 中标结果公告.md
```

## 关键技术点
1. **网络拦截**: `page.on('request')` 捕获 PDF 下载 URL 和 Headers
2. **请求头复用**: 使用浏览器原始请求的 Headers 下载 PDF
3. **pdfplumber 表格提取**: `page.extract_tables()` 精准识别表格结构
4. **空值保留**: 空字段统一设为"未披露"

## 下一步
- 重启 Claude Code 以激活 camoufox-reverse MCP
- 可使用 MCP 的 35 个逆向分析工具
