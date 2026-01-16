# 微信公众号文章数据获取系统

一个功能完整的微信公众号文章数据获取系统，支持自动化获取文章内容、统计数据（阅读量、点赞量、分享量、评论量）和留言区内容。

## 核心功能

- ✅ **完整HTML下载**：下载包含完整样式的文章HTML，自动内联CSS
- ✅ **统计数据提取**：从HTML中提取阅读量、点赞量、分享量、评论量
- ✅ **留言区获取**：自动获取并注入精选留言到HTML
- ✅ **参数自动捕获**：自动捕获微信认证参数，无需手动配置
- ✅ **数据库缓存**：使用PostgreSQL数据库缓存文章和参数
- ✅ **批量获取**：支持按日期范围批量获取文章
- ✅ **智能增量**：自动检测已有数据，只获取缺失部分
- ✅ **RESTful API**：提供完整的HTTP API接口

## 系统架构

```
┌─────────────────┐
│   API 客户端    │
└────────┬────────┘
         │ HTTP Request
         ▼
┌─────────────────┐
│  API Server     │ ← Flask服务器
│  (api_server.py)│
└────────┬────────┘
         │
    ┌────┴────┬──────────────┬──────────────┐
    ▼         ▼              ▼              ▼
┌────────┐ ┌──────┐  ┌──────────┐  ┌──────────┐
│ 数据库 │ │ 参数 │  │ 微信自动 │  │ HTML下载 │
│ 缓存   │ │ 捕获 │  │ 化操作   │  │ & 提取   │
└────────┘ └──────┘  └──────────┘  └──────────┘
```

## 快速开始

### 1. 环境要求

- Python 3.9+
- Windows 10/11（用于微信PC端自动化）
- 微信PC版（已登录）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- Flask - Web框架
- SQLAlchemy - ORM
- requests - HTTP请求
- BeautifulSoup4 - HTML解析
- pywinauto - Windows自动化
- mitmproxy - 代理服务器

### 3. 启动服务

```bash
# Windows
start_api_server.bat

# 或带日志输出
start_api_with_log.bat
```

服务将在 `http://localhost:5001` 启动

### 4. 配置数据库

确保 PostgreSQL 服务运行在 localhost:5435：

```sql
CREATE DATABASE wechat_articles;
CREATE USER wechat WITH PASSWORD 'wechat123';
GRANT ALL PRIVILEGES ON DATABASE wechat_articles TO wechat;
```

首次启动时会自动创建数据库表。

## API 接口

### 1. 健康检查

```http
GET /api/health
```

**响应示例：**
```json
{
  "status": "ok",
  "timestamp": "2025-12-13T18:00:00",
  "service": "WeChat Articles API"
}
```

### 2. 获取单篇文章（V2 - 推荐）

```http
POST /api/v2/fetch_article
Content-Type: application/json

{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx"
}
```

**功能：**
- 自动检查数据库缓存（24小时内有效）
- 缓存失效时自动重新获取
- 参数不存在时自动捕获

**响应示例：**
```json
{
  "success": true,
  "data": {
    "account_name": "公众号名称",
    "biz": "MzYzNDE2Mzk2NQ==",
    "from_cache": false,
    "title": "文章标题",
    "url": "https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx...",
    "read_count": 60790,
    "like_count": 245,
    "old_like_count": 180,
    "favorite_count": 245,
    "share_count": 89,
    "comment_count": 42,
    "publish_date": "2025-12-06",
    "html_content": "...",
    "local_html_path": "articles_html/2025-12-06-文章标题_FULL.html"
  }
}
```

### 3. 批量获取文章（V2 - 推荐）

```http
POST /api/v2/fetch_articles_filtered
Content-Type: application/json

{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",
  "start_date": "2025-12-01",
  "end_date": "2025-12-10",
  "min_read_count": 10000,
  "limit": 20
}
```

**功能：**
- 按日期范围批量获取
- 智能增量更新（只获取缺失日期的文章）
- 支持阅读量过滤
- 自动下载完整HTML + 统计数据 + 留言

**响应示例：**
```json
{
  "success": true,
  "data": {
    "account_name": "公众号名称",
    "biz": "MzYzNDE2Mzk2NQ==",
    "from_cache": false,
    "total_saved": 5,
    "total": 10,
    "articles": [
      {
        "title": "文章标题",
        "url": "https://mp.weixin.qq.com/s?__biz=xxx...",
        "read_count": 60790,
        "like_count": 245,
        "share_count": 89,
        "comment_count": 42,
        "publish_date": "2025-12-06",
        "local_html_path": "articles_html/2025-12-06-文章标题_FULL.html"
      }
    ]
  }
}
```

### 4. 智能批量获取（完全自动化）

```http
POST /api/fetch_articles_smart
Content-Type: application/json

{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",
  "start_date": "2025-12-01",
  "end_date": "2025-12-10"
}
```

**功能：**
- 完全模拟 `smart_batch_auto.py` 的工作流程
- 自动检查参数有效性
- 参数失效时自动重新捕获
- 智能增量更新
- 返回完整日期范围的所有文章（已有+新获取）

## 核心模块说明

### API 服务层

- **api_server.py** - Flask主服务器，处理HTTP请求
- **api_endpoints_new.py** - V2 API端点，支持数据库缓存
- **api_endpoints_smart.py** - 智能API端点，完全自动化

### 数据库层

- **database.py** - 数据库连接和初始化
- **models.py** - SQLAlchemy数据模型
- **db_operations.py** - 数据库CRUD操作
- **db_helpers.py** - 数据库辅助函数

### 核心功能模块

- **smart_batch_fetch.py** - 批量获取文章列表
- **download_full_html.py** - 下载完整HTML（含统计数据）
- **extract_stats_from_html.py** - 从HTML提取统计数据
- **get_comments_improved.py** - 获取文章留言
- **inject_comments_dom.py** - 将留言注入到HTML

### 自动化模块

- **capture_new_wechat.py** - 代理服务器，捕获微信参数
- **capture_process.py** - 捕获进程管理
- **wechat_automation.py** - 微信PC端自动化操作

## 工作流程

### 参数捕获流程

```
1. 启动代理服务器（监听8888端口）
   ↓
2. 设置系统代理
   ↓
3. 自动化操作：打开微信 → 文件传输助手 → 发送文章链接
   ↓
4. 代理拦截请求，提取参数（KEY, UIN, PASS_TICKET, COOKIE）
   ↓
5. 保存参数到 params/biz_{BIZ}/config.py
   ↓
6. 关闭代理，恢复系统设置
```

### 文章获取流程

```
1. 检查数据库是否有该BIZ的有效参数
   ↓
2. 无参数或参数失效 → 触发自动捕获
   ↓
3. 使用参数调用微信API获取文章列表
   ↓
4. 对每篇文章：
   - 下载完整HTML（参数化请求）
   - 从HTML提取统计数据
   - 获取留言并注入到HTML
   - 保存到数据库
   ↓
5. 返回结果
```

## 数据存储

### 数据库表结构

**accounts** - 公众号账号
- id, biz, name, created_at, updated_at

**parameters** - 认证参数
- id, biz, cookie, key, pass_ticket, uin, appmsg_token
- is_valid, captured_at, expires_at

**articles** - 文章数据
- id, biz, url, short_url, title, html_content
- publish_date, read_count, like_count, old_like_count
- favorite_count, share_count, comment_count
- local_html_path, created_at, updated_at

### 文件存储

- **articles_html/** - 下载的完整HTML文件
  - 格式：`YYYY-MM-DD-文章标题_FULL.html`
  - 包含：完整样式、统计数据、留言区

- **params/** - 参数配置文件
  - `new_wechat_config.py` - 通用参数配置
  - `biz_{BIZ}/config.py` - BIZ专属参数

## 统计数据说明

从HTML中提取的统计数据包括：

- **read_num** - 阅读量（`var read_num_new = '60790'`）
- **old_like_count** - 点赞数/大拇指👍（`old_like_count: '180'`）
- **like_count** - 喜欢数/爱心❤️（`like_count: '245'`）
- **share_count** - 分享数（`share_count: '89'`）
- **comment_count** - 评论数（`comment_count: '42'`）

## 留言区功能

系统会自动：
1. 从HTML中提取 `comment_id`
2. 调用微信留言API获取精选留言
3. 使用CSS样式渲染留言区
4. 将留言直接注入到HTML文件

留言区包含：
- 用户头像、昵称、留言内容
- 留言时间、点赞数
- 作者回复（特殊样式）
- 二级留言（用户回复）

## 参数有效期

微信参数有时间限制，通常：
- **有效期**：几小时到几天不等
- **失效标志**：API返回 `no session` 或 `params is error`
- **自动处理**：系统检测到失效时自动重新捕获

## 常见问题

### 1. 参数捕获失败

**原因：**
- 微信未登录
- 代理设置失败
- 文章链接错误

**解决：**
- 确保微信PC版已登录
- 检查防火墙设置
- 使用该公众号的其他文章链接

### 2. 统计数据为0

**原因：**
- 参数已失效
- HTML中没有统计数据变量

**解决：**
- 重新捕获参数
- 检查文章是否太旧（旧文章可能没有统计数据）

### 3. 留言获取失败

**原因：**
- 文章未开启留言功能
- 留言API返回空响应

**解决：**
- 检查文章是否有留言
- 确认参数有效性

## 技术特点

1. **参数化请求**：使用 KEY、UIN、PASS_TICKET 等参数构造请求，获取包含统计数据的HTML
2. **HTML解析**：使用正则表达式从HTML中提取统计数据变量
3. **CSS内联**：自动下载并内联外部CSS，确保HTML离线可用
4. **代理捕获**：使用mitmproxy拦截微信请求，自动提取认证参数
5. **自动化操作**：使用pywinauto控制微信PC端，实现全自动化
6. **数据库缓存**：使用PostgreSQL缓存数据，避免重复请求

## 开发者信息

- **项目类型**：微信公众号数据采集系统
- **开发语言**：Python 3.9+
- **主要框架**：Flask, SQLAlchemy
- **适用平台**：Windows 10/11

## 许可证

本项目仅供学习和研究使用，请勿用于商业目的。使用本项目时请遵守微信公众平台的相关规定。

## 更新日志

### v2.0 (2025-12-13)
- ✅ 集成完整HTML下载功能
- ✅ 支持从HTML提取统计数据
- ✅ 新增留言区获取和注入功能
- ✅ 优化参数捕获流程
- ✅ 添加数据库缓存机制
- ✅ 实现智能增量更新

### v1.0
- 基础API功能
- 文章列表获取
- 统计数据API调用
