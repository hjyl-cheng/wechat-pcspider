# 微信公众号文章数据采集系统 - 完整项目文档

## 📋 项目概述

这是一个功能完整的**微信公众号文章数据获取系统**，支持自动化获取文章内容、统计数据（阅读量、点赞量、分享量、评论量）和留言区内容。

### 核心特性

- ✅ **完整HTML下载**：下载包含完整样式的文章HTML，自动内联CSS
- ✅ **统计数据提取**：从HTML中提取阅读量、点赞量、分享量、评论量
- ✅ **留言区获取**：自动获取并注入精选留言到HTML
- ✅ **参数自动捕获**：自动捕获微信认证参数，无需手动配置
- ✅ **数据库缓存**：使用PostgreSQL数据库缓存文章和参数
- ✅ **批量获取**：支持按日期范围批量获取文章
- ✅ **智能增量**：自动检测已有数据，只获取缺失部分
- ✅ **RESTful API**：提供完整的HTTP API接口

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    API 客户端                                │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Request
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Flask API Server (5001)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ api_server.py / api_endpoints_new.py /               │   │
│  │ api_endpoints_smart.py                               │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
         ┌──────────────┼──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
    ┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ 数据库 │  │ 参数捕获 │  │ 微信自动 │  │ HTML下载 │
    │ 缓存   │  │ 代理     │  │ 化操作   │  │ & 提取   │
    │ (PG)   │  │ (8080)   │  │ (PC)     │  │ 统计数据 │
    └────────┘  └──────────┘  └──────────┘  └──────────┘
         │              │              │              │
         └──────────────┼──────────────┴──────────────┘
                        ▼
            ┌──────────────────────────┐
            │  微信公众号平台          │
            │  (mp.weixin.qq.com)      │
            └──────────────────────────┘
```

---

## 📁 项目结构

```
wechat_articles_spider/
│
├── 📂 核心模块
│   ├── api_server.py              # Flask主服务器
│   ├── api_endpoints_new.py       # V2 API端点（推荐）
│   ├── api_endpoints_smart.py     # 智能API端点（全自动化）
│   ├── database.py                # 数据库连接管理
│   ├── models.py                  # SQLAlchemy ORM模型
│   ├── db_operations.py           # 数据库CRUD操作
│   └── db_helpers.py              # 数据库辅助函数
│
├── 📂 采集模块
│   ├── capture_new_wechat.py      # 代理参数捕获器
│   ├── capture_process.py         # 参数捕获进程包装器
│   ├── smart_batch_fetch.py       # 批量获取文章列表
│   ├── download_full_html.py      # 下载完整HTML
│   ├── extract_stats_from_html.py # 从HTML提取统计数据
│   ├── get_comments_improved.py   # 获取文章留言
│   └── inject_comments_dom.py     # 注入留言到HTML
│
├── 📂 自动化模块
│   └── wechat_automation.py       # 微信PC端自动化操作
│
├── 📂 工具模块
│   ├── check_articles.py          # 检查文章数据
│   ├── check_date_issue.py        # 检查日期问题
│   ├── clear_articles.py          # 清理文章数据
│   ├── fix_html_referrer.py       # 修复HTML防盗链
│   ├── migrate_database.py        # 数据库迁移（SQLite）
│   ├── migrate_database_postgres.py # 数据库迁移（PostgreSQL）
│   ├── remove_favorite_count.py   # 移除收藏数
│   ├── show_article_dates.py      # 显示文章日期
│   └── backup_database.py         # 数据库备份
│
├── 📂 wechatarticles/             # 微信文章核心库
│   ├── ArticlesInfo.py            # 文章信息获取
│   └── proxy/                     # 代理服务器模块
│
├── 📂 params/                     # 参数配置目录
│   ├── new_wechat_config.py       # 通用参数配置
│   ├── biz_{BIZ}/                 # BIZ专属参数目录
│   │   ├── config.py              # Python配置
│   │   ├── params.json            # JSON配置
│   │   └── params_latest.txt      # 文本配置
│   ├── ca.crt                     # CA证书
│   └── ca.pem                     # CA证书（PEM格式）
│
├── 📂 articles_html/              # 下载的HTML文件
│   └── {公众号名称}/
│       └── {日期}/
│           └── {文章标题}.html
│
├── 📂 backup/                     # 数据库备份
│   └── wechat_db_backup_*.json
│
├── 📂 test/                       # 测试文件
│
├── 📄 配置文件
│   ├── requirements.txt           # Python依赖
│   ├── setup.py                   # 安装配置
│   ├── setup.cfg                  # 安装配置
│   └── .gitignore                 # Git忽略规则
│
├── 📄 启动脚本
│   ├── start_api_server.bat       # 启动API服务
│   └── start_api_with_log.bat     # 带日志启动
│
└── 📄 文档
    ├── README.md                  # 项目说明
    ├── API_DOCUMENTATION.md       # API文档
    ├── PROJECT_DOCUMENTATION.md   # 完整项目文档（本文件）
    └── LICENSE                    # 许可证
```

---

## 💾 数据库设计

### 数据库配置

- **类型**: PostgreSQL
- **主机**: localhost
- **端口**: 5435
- **数据库**: wechat_articles
- **用户**: wechat / wechat123
- **连接池**: pool_size=10, max_overflow=20

### 数据表结构

#### accounts 表 - 公众号账号

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| biz | String(100) | 公众号BIZ标识（唯一索引） |
| name | String(200) | 公众号名称 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### parameters 表 - 认证参数

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| biz | String(100) | 公众号BIZ（外键） |
| cookie | Text | Cookie |
| key | Text | 认证密钥 |
| pass_ticket | Text | 通行票据 |
| uin | Text | 用户ID |
| appmsg_token | Text | 消息Token |
| captured_at | DateTime | 捕获时间 |
| expires_at | DateTime | 过期时间（通常4小时） |
| is_valid | Boolean | 参数有效性标志（索引） |
| created_at | DateTime | 创建时间 |

#### articles 表 - 文章数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| biz | String(100) | 公众号BIZ（外键，索引） |
| url | Text | 完整URL（唯一） |
| short_url | Text | 短链接（索引） |
| title | Text | 文章标题 |
| html_content | Text | HTML内容 |
| publish_date | Date | 发布日期（索引） |
| read_count | Integer | 阅读量（索引） |
| old_like_count | Integer | 点赞数（大拇指👍） |
| like_count | Integer | 喜欢数/收藏数（爱心❤️） |
| share_count | Integer | 分享数 |
| comment_count | Integer | 评论数 |
| local_html_path | Text | 本地HTML文件路径 |
| fetched_at | DateTime | 抓取时间（索引） |

---

## 🔌 API 接口

### 基础信息

- **基础URL**: `http://localhost:5001`
- **数据格式**: JSON
- **字符编码**: UTF-8

### 接口列表

#### 1. 健康检查

```http
GET /api/health
```

**响应示例：**
```json
{
  "status": "ok",
  "timestamp": "2026-01-16T08:00:00",
  "service": "WeChat Articles API"
}
```

#### 2. 获取单篇文章（V2 - 推荐）

```http
POST /api/v2/fetch_article
Content-Type: application/json

{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx"
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "title": "文章标题",
    "url": "https://mp.weixin.qq.com/s?__biz=xxx...",
    "publish_date": "2026-01-15",
    "read_count": 60790,
    "like_count": 245,
    "old_like_count": 180,
    "share_count": 89,
    "comment_count": 42,
    "local_html_path": "articles_html/公众号/2026-01-15/文章标题.html",
    "from_cache": false
  }
}
```

#### 3. 批量获取文章（V2 - 推荐）

```http
POST /api/v2/fetch_articles_filtered
Content-Type: application/json

{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",
  "start_date": "2026-01-01",
  "end_date": "2026-01-15",
  "min_read_count": 1000
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "account_name": "公众号名称",
    "biz": "MzYzNDE2Mzk2NQ==",
    "from_cache": false,
    "total": 10,
    "new_fetched": 5,
    "articles": [
      {
        "id": 123,
        "title": "文章标题",
        "url": "https://mp.weixin.qq.com/s?__biz=xxx...",
        "publish_date": "2026-01-06",
        "read_count": 60790,
        "like_count": 245,
        "old_like_count": 180,
        "share_count": 89,
        "comment_count": 42,
        "local_html_path": "articles_html/公众号/2026-01-06/文章标题.html"
      }
    ]
  }
}
```

#### 4. 智能批量获取（全自动化）

```http
POST /api/fetch_articles_smart
Content-Type: application/json

{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",
  "start_date": "2026-01-01",
  "end_date": "2026-01-15"
}
```

此接口完全模拟自动化工作流程，参数失效时会自动重新捕获。

#### 5. 静态HTML文件访问

```http
GET /articles/{公众号名称}/{日期}/{文件名}.html
```

---

## ⚙️ 核心工作流程

### 1. 参数捕获流程

```
1. 启动代理服务器（监听8080端口）
   ↓
2. 设置系统代理（Windows注册表）
   ↓
3. 自动化操作：打开微信 → 文件传输助手 → 发送文章链接
   ↓
4. 代理拦截请求，提取参数（KEY, UIN, PASS_TICKET, COOKIE）
   ↓
5. 保存参数到 params/biz_{BIZ}/config.py 和数据库
   ↓
6. 关闭代理，恢复系统设置
```

### 2. 文章获取流程

```
1. 检查数据库是否有该BIZ的有效参数
   ↓
2. 无参数或参数失效 → 触发自动捕获
   ↓
3. 使用参数调用微信API获取文章列表
   ↓
4. 对每篇文章：
   - 下载完整HTML（参数化请求）
   - 从HTML提取统计数据（正则表达式）
   - 获取留言并注入到HTML
   - 保存到数据库
   ↓
5. 返回结果
```

### 3. 统计数据提取

从HTML中提取的统计数据变量：
- `read_num_new` - 阅读量
- `old_like_count` - 点赞数（大拇指👍）
- `like_count` - 喜欢数/收藏数（爱心❤️）
- `share_count` - 分享数
- `comment_count` - 评论数

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.9+
- PostgreSQL 12+
- Windows 10/11（用于微信PC端自动化）
- 微信PC版（已登录）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库

确保 PostgreSQL 服务运行在 localhost:5435，并创建数据库：

```sql
CREATE DATABASE wechat_articles;
CREATE USER wechat WITH PASSWORD 'wechat123';
GRANT ALL PRIVILEGES ON DATABASE wechat_articles TO wechat;
```

### 4. 启动服务

```bash
# Windows
start_api_server.bat

# 或带日志输出
start_api_with_log.bat

# 或直接运行
python api_server.py
```

服务将在 `http://localhost:5001` 启动

---

## 📦 主要依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Flask | 3.1.2 | Web框架 |
| SQLAlchemy | 2.0.45 | ORM |
| psycopg2-binary | 2.9.11 | PostgreSQL驱动 |
| requests | 2.32.5 | HTTP请求 |
| BeautifulSoup4 | 4.14.3 | HTML解析 |
| pywinauto | >=0.6.0 | Windows自动化 |
| pyperclip | >=1.8.0 | 剪贴板操作 |
| pywin32 | >=300 | Windows API |
| lxml | 6.0.2 | XML/HTML解析 |

---

## 🔧 配置说明

### 参数配置文件

参数配置保存在 `params/` 目录下：

**通用配置** (`params/new_wechat_config.py`):
```python
COOKIE = '...'
KEY = '...'
PASS_TICKET = '...'
UIN = '...'
DEVICETYPE = 'Windows'
CLIENTVERSION = '...'
BIZ = '...'
```

**BIZ专属配置** (`params/biz_{BIZ}/config.py`):
每个公众号有独立的参数文件，自动生成和更新。

### 证书文件

代理服务器需要CA证书：
- `test/ca.pem` - CA证书（PEM格式）
- `test/ca.crt` - CA证书（CRT格式）

---

## 📊 数据备份

### 使用备份脚本

```bash
python backup_database.py
```

备份文件保存在 `backup/` 目录，格式为 JSON。

### 备份内容

- 公众号账号信息
- 认证参数（敏感信息已截断）
- 文章数据（不含HTML内容）
- 统计信息

---

## ⚠️ 注意事项

1. **参数有效期**：微信认证参数通常4小时过期，需要定期重新捕获
2. **Windows平台**：自动化操作仅支持Windows系统
3. **微信版本**：需要使用PC版微信，并保持登录状态
4. **API限制**：微信API可能有频率限制，建议适当控制请求频率
5. **验证码**：某些文章可能需要验证码，暂不支持自动处理
6. **旧文章**：发布时间较早的文章可能没有统计数据

---

## 📝 更新日志

### v2.0.0 (2026-01)
- 迁移到 PostgreSQL 数据库
- 新增智能批量获取API
- 优化参数自动捕获流程
- 添加留言注入功能
- 完善项目文档

### v1.0.0 (2025-12)
- 初始版本
- 基础文章获取功能
- SQLite 数据库支持

---

## 📄 许可证

MIT License
