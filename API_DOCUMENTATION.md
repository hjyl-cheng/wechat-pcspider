# 微信公众号文章数据获取 API 文档

## 服务信息

- **服务地址**: `http://localhost:5001`
- **协议**: HTTP/REST
- **数据格式**: JSON
- **数据库**: PostgreSQL (Docker容器)

---

## API 端点列表

### 1. 健康检查

**端点**: `GET /api/health`

**描述**: 检查服务是否正常运行

**请求**: 无需参数

**响应示例**:
```json
{
  "status": "ok",
  "timestamp": "2025-12-13T18:00:00",
  "service": "WeChat Articles API"
}
```

---

### 2. 获取单篇文章（旧版）

**端点**: `POST /api/fetch_article`

**描述**: 获取单篇文章的统计数据（不使用数据库缓存）

**请求体**:
```json
{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",
  "fetch_time": "2025-12-13T18:00:00"  // 可选
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "title": "文章标题",
    "url": "https://mp.weixin.qq.com/s/xxxxx",
    "read_count": 10000,
    "old_like_count": 150,
    "like_count": 200,
    "share_count": 50,
    "comment_count": 30,
    "publish_date": "2025-12-01",
    "local_html_path": "articles_html/公众号/2025-12-01/文章标题.html"
  }
}
```

**特性**:
- 自动检测参数有效性
- 参数失效时自动捕获新参数
- 下载完整HTML（包含CSS和图片）
- 提取并注入评论到HTML

---

### 3. 获取单篇文章（新版，推荐）⭐

**端点**: `POST /api/v2/fetch_article`

**描述**: 获取单篇文章数据，使用数据库缓存，避免重复请求

**请求体**:
```json
{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",
  "force_refresh": false  // 可选，强制刷新
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 123,
    "biz": "MzI2MzU2ODM5OA==",
    "title": "文章标题",
    "url": "https://mp.weixin.qq.com/s/xxxxx",
    "short_url": "https://mp.weixin.qq.com/s/xxxxx",
    "publish_date": "2025-12-01",
    "read_count": 10000,
    "old_like_count": 150,
    "like_count": 200,
    "share_count": 50,
    "comment_count": 30,
    "local_html_path": "articles_html/公众号/2025-12-01/文章标题.html",
    "html_url": "/articles/公众号/2025-12-01/文章标题.html",
    "fetched_at": "2025-12-13T18:00:00",
    "from_cache": true
  }
}
```

**特性**:
- ✅ 数据库缓存（避免重复请求）
- ✅ 自动参数管理
- ✅ 完整HTML下载
- ✅ 评论注入
- ✅ 支持强制刷新

---

### 4. 批量获取文章（带过滤，推荐）⭐⭐⭐

**端点**: `POST /api/v2/fetch_articles_filtered`

**描述**: 批量获取公众号文章，支持日期过滤和增量更新

**请求体**:
```json
{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",  // 任意一篇文章URL
  "start_date": "2025-12-01",
  "end_date": "2025-12-10",
  "min_read_count": 1000  // 可选，最小阅读数过滤
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "articles": [
      {
        "id": 123,
        "biz": "MzI2MzU2ODM5OA==",
        "title": "文章标题1",
        "url": "https://mp.weixin.qq.com/s/xxxxx",
        "publish_date": "2025-12-05",
        "read_count": 15000,
        "old_like_count": 200,
        "like_count": 300,
        "share_count": 80,
        "comment_count": 45,
        "local_html_path": "articles_html/公众号/2025-12-05/文章标题1.html",
        "fetched_at": "2025-12-13T18:00:00"
      },
      {
        "id": 124,
        "title": "文章标题2",
        ...
      }
    ],
    "total": 10,
    "from_cache": 5,
    "newly_fetched": 5
  }
}
```

**特性**:
- ✅ 智能增量更新（只获取缺失的文章）
- ✅ 日期范围过滤
- ✅ 阅读数过滤
- ✅ 数据库缓存
- ✅ 自动参数捕获
- ✅ 批量下载HTML
- ✅ 批量注入评论

**工作流程**:
1. 检查数据库中已有的文章
2. 识别缺失的日期范围
3. 只从微信API获取缺失的文章
4. 下载完整HTML并提取统计数据
5. 保存到数据库
6. 返回所有符合条件的文章

---

### 5. 批量获取文章（旧版）

**端点**: `POST /api/fetch_articles`

**描述**: 批量获取文章（不使用数据库）

**请求体**:
```json
{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",
  "count": 10  // 获取数量
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "articles": [...],
    "total": 10
  }
}
```

---

### 6. 智能批量获取（完全自动化）⭐⭐⭐

**端点**: `POST /api/fetch_articles_smart`

**描述**: 最智能的批量获取方式，完全自动化处理

**请求体**:
```json
{
  "account_name": "公众号名称",
  "article_url": "https://mp.weixin.qq.com/s/xxxxx",
  "start_date": "2025-12-01",
  "end_date": "2025-12-10",
  "auto_capture": true  // 自动捕获参数
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "articles": [...],
    "total": 15,
    "statistics": {
      "total_read": 150000,
      "total_like": 3000,
      "avg_read": 10000
    }
  }
}
```

**特性**:
- ✅ 完全自动化
- ✅ 自动参数捕获
- ✅ 智能增量更新
- ✅ 统计数据汇总
- ✅ 错误自动重试

---

### 7. 停止代理服务器

**端点**: `POST /api/stop_proxy`

**描述**: 手动停止代理服务器（通常自动管理）

**请求**: 无需参数

**响应示例**:
```json
{
  "success": true,
  "message": "代理服务器已停止"
}
```

---

## 数据模型

### Article（文章）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| biz | String | 公众号BIZ标识 |
| url | Text | 完整URL |
| short_url | Text | 短链接 |
| title | Text | 文章标题 |
| html_content | Text | HTML内容（可选） |
| publish_date | Date | 发布日期 |
| read_count | Integer | 阅读量 |
| old_like_count | Integer | 点赞数（大拇指👍） |
| like_count | Integer | 喜欢数/收藏数（爱心❤️） |
| share_count | Integer | 分享数 |
| comment_count | Integer | 评论数 |
| local_html_path | Text | 本地HTML文件路径 |
| html_url | String | 可访问的HTML URL（相对路径） |
| fetched_at | DateTime | 抓取时间 |

### Account（公众号）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| biz | String | 公众号BIZ（唯一） |
| name | String | 公众号名称 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### Parameter（参数）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| biz | String | 公众号BIZ |
| cookie | Text | Cookie |
| key | Text | Key |
| pass_ticket | Text | Pass Ticket |
| uin | Text | UIN |
| appmsg_token | Text | AppMsg Token |
| captured_at | DateTime | 捕获时间 |
| expires_at | DateTime | 过期时间 |
| is_valid | Boolean | 是否有效 |

---

## 错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |

**错误响应格式**:
```json
{
  "success": false,
  "error": "错误描述信息"
}
```

---

## 使用建议

### 推荐的API使用顺序

1. **首次使用**: 使用 `/api/v2/fetch_article` 获取单篇文章，系统会自动捕获参数
2. **批量获取**: 使用 `/api/v2/fetch_articles_filtered` 批量获取指定日期范围的文章
3. **增量更新**: 再次调用 `/api/v2/fetch_articles_filtered`，系统会自动识别并只获取新文章

### 最佳实践

1. **使用数据库缓存**: 优先使用 `/api/v2/*` 端点，避免重复请求
2. **合理设置日期范围**: 不要一次性获取太长时间跨度的文章
3. **监控参数有效性**: 系统会自动管理，但可以通过日志监控
4. **本地HTML存储**: 完整HTML保存在 `articles_html/` 目录，包含CSS和图片

### 性能优化

- 数据库使用连接池（pool_size=10）
- 自动检测并跳过已存在的文章
- 智能增量更新，减少API调用
- 本地HTML缓存，避免重复下载

---

## 数据库配置

**连接信息** (Docker容器):
```
Host: localhost
Port: 5435
Database: wechat_articles
User: wechat
Password: wechat123
```

**迁移脚本**:
- `migrate_database_postgres.py` - PostgreSQL数据库迁移
- `remove_favorite_count.py` - 清理重复字段

---

## 常见问题

### Q: 如何处理参数失效？
A: 系统会自动检测参数有效性，失效时自动启动微信自动化捕获新参数。

### Q: 如何避免重复获取文章？
A: 使用 `/api/v2/fetch_articles_filtered`，系统会自动检查数据库并只获取缺失的文章。

### Q: HTML文件保存在哪里？
A: `articles_html/{公众号名称}/{发布日期}/{文章标题}.html`

### Q: 如何查看数据库中的文章？
A: 运行 `python check_articles.py` 或 `python show_article_dates.py`

### Q: 为什么查询返回0篇文章？
A: 检查数据库中是否有该日期的文章，使用 `show_article_dates.py` 查看实际日期分布。

---

## 示例代码

### Python 示例

```python
import requests

# 1. 健康检查
response = requests.get('http://localhost:5001/api/health')
print(response.json())

# 2. 获取单篇文章
response = requests.post('http://localhost:5001/api/v2/fetch_article', json={
    'account_name': '涂磊',
    'article_url': 'https://mp.weixin.qq.com/s/xxxxx'
})
print(response.json())

# 3. 批量获取文章（推荐）
response = requests.post('http://localhost:5001/api/v2/fetch_articles_filtered', json={
    'account_name': '涂磊',
    'article_url': 'https://mp.weixin.qq.com/s/xxxxx',
    'start_date': '2025-11-29',
    'end_date': '2025-12-04',
    'min_read_count': 1000
})
data = response.json()
print(f"获取到 {data['data']['total']} 篇文章")
for article in data['data']['articles']:
    print(f"- {article['title']}: {article['read_count']} 阅读")
```

### JavaScript 示例

```javascript
// 批量获取文章
fetch('http://localhost:5001/api/v2/fetch_articles_filtered', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    account_name: '涂磊',
    article_url: 'https://mp.weixin.qq.com/s/xxxxx',
    start_date: '2025-11-29',
    end_date: '2025-12-04'
  })
})
.then(response => response.json())
.then(data => {
  console.log(`获取到 ${data.data.total} 篇文章`);
  data.data.articles.forEach(article => {
    console.log(`${article.title}: ${article.read_count} 阅读`);
  });
});
```

---

## 更新日志

### v2.0 (2025-12-13)
- ✅ 添加 PostgreSQL 数据库支持
- ✅ 实现智能增量更新
- ✅ 添加数据库缓存机制
- ✅ 优化参数自动捕获流程
- ✅ 合并 favorite_count 和 like_count 字段
- ✅ 添加完整HTML下载和评论注入功能

### v1.0
- 初始版本
- 基础文章获取功能
