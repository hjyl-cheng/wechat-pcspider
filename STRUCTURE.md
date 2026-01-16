# 项目结构说明

## 目录结构

```
wechat_articles_spider/
│
├── 📂 核心模块 (Core Modules)
│   ├── api_server.py              # Flask主服务器入口
│   ├── api_endpoints_new.py       # V2 API端点（推荐使用）
│   ├── api_endpoints_smart.py     # 智能API端点（全自动化）
│   ├── database.py                # PostgreSQL数据库连接管理
│   ├── models.py                  # SQLAlchemy ORM模型定义
│   ├── db_operations.py           # 数据库CRUD操作函数
│   └── db_helpers.py              # 数据库辅助查询函数
│
├── 📂 采集模块 (Capture Modules)
│   ├── capture_new_wechat.py      # 代理服务器参数捕获器
│   ├── capture_process.py         # 参数捕获进程包装器
│   ├── smart_batch_fetch.py       # 批量获取文章列表和统计
│   ├── download_full_html.py      # 下载完整HTML（含CSS内联）
│   ├── extract_stats_from_html.py # 从HTML提取统计数据
│   ├── get_comments_improved.py   # 获取文章留言
│   └── inject_comments_dom.py     # 注入留言到HTML
│
├── 📂 自动化模块 (Automation)
│   └── wechat_automation.py       # 微信PC端自动化操作
│
├── 📂 工具脚本 (Utilities)
│   ├── check_articles.py          # 检查文章数据
│   ├── check_date_issue.py        # 检查日期问题
│   ├── clear_articles.py          # 清理文章数据
│   ├── fix_html_referrer.py       # 修复HTML防盗链
│   ├── migrate_database.py        # SQLite数据库迁移
│   ├── migrate_database_postgres.py # PostgreSQL迁移
│   ├── remove_favorite_count.py   # 移除收藏数字段
│   ├── show_article_dates.py      # 显示文章日期
│   └── backup_database.py         # 数据库备份脚本
│
├── 📂 wechatarticles/             # 微信文章核心库
│   ├── ArticlesInfo.py            # 文章信息获取类
│   └── proxy/                     # 代理服务器模块
│
├── 📂 params/                     # 参数配置目录
│   ├── new_wechat_config.py       # 通用参数配置
│   ├── biz_{BIZ}/                 # BIZ专属参数目录
│   ├── ca.crt                     # CA证书
│   └── ca.pem                     # CA证书（PEM格式）
│
├── 📂 articles_html/              # 下载的HTML文件存储
│   └── {公众号名称}/{日期}/       # 按公众号和日期组织
│
├── 📂 backup/                     # 数据库备份目录
│
├── 📂 scripts/                    # 辅助脚本
│   └── cleanup_project.py         # 项目清理脚本
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
    ├── API_DOCUMENTATION.md       # API接口文档
    ├── PROJECT_DOCUMENTATION.md   # 完整项目文档
    ├── STRUCTURE.md               # 项目结构说明（本文件）
    └── LICENSE                    # 许可证
```

## 模块依赖关系

```
api_server.py
    ├── api_endpoints_new.py
    │   ├── db_operations.py
    │   ├── db_helpers.py
    │   ├── smart_batch_fetch.py
    │   └── download_full_html.py
    │
    ├── api_endpoints_smart.py
    │   ├── smart_batch_fetch.py
    │   ├── download_full_html.py
    │   ├── extract_stats_from_html.py
    │   └── db_operations.py
    │
    ├── database.py
    │   └── models.py
    │
    └── wechatarticles/
        └── ArticlesInfo.py

capture_new_wechat.py
    └── wechatarticles/proxy/

wechat_automation.py
    └── pywinauto (外部库)
```

## 数据流向

```
用户请求 → API Server → 检查数据库缓存
                            ↓
                    缓存有效？ ─── 是 ──→ 返回缓存数据
                            │
                           否
                            ↓
                    检查参数有效性
                            ↓
                    参数有效？ ─── 否 ──→ 自动捕获参数
                            │                    ↓
                           是 ←─────────────────┘
                            ↓
                    调用微信API获取文章列表
                            ↓
                    下载HTML + 提取统计数据
                            ↓
                    获取并注入留言
                            ↓
                    保存到数据库
                            ↓
                    返回结果
```
