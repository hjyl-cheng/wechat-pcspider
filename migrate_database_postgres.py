# coding: utf-8
"""
PostgreSQL 数据库迁移脚本（Docker 容器版本）
添加新字段：old_like_count, share_count, local_html_path
"""
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """迁移 PostgreSQL 数据库，添加新字段"""
    
    # Docker 容器中的 PostgreSQL 连接信息
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5435,
        'database': 'wechat_articles',
        'user': 'wechat',
        'password': 'wechat123'
    }
    
    logger.info(f"开始迁移 PostgreSQL 数据库（Docker 容器）...")
    logger.info(f"连接信息: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    try:
        # 连接数据库
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True  # 自动提交模式
        cursor = conn.cursor()
        
        logger.info(f"✅ 已连接到数据库: {DB_CONFIG['database']}")
        
        # 检查并添加 old_like_count 字段
        try:
            cursor.execute("SELECT old_like_count FROM articles LIMIT 1")
            logger.info("✅ old_like_count 字段已存在")
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()  # 回滚失败的查询
            logger.info("添加 old_like_count 字段...")
            cursor.execute("ALTER TABLE articles ADD COLUMN old_like_count INTEGER")
            logger.info("✅ 已添加 old_like_count 字段")
        except Exception as e:
            conn.rollback()
            logger.warning(f"检查 old_like_count 字段时出错: {e}")
        
        # 检查并添加 share_count 字段
        try:
            cursor.execute("SELECT share_count FROM articles LIMIT 1")
            logger.info("✅ share_count 字段已存在")
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()  # 回滚失败的查询
            logger.info("添加 share_count 字段...")
            cursor.execute("ALTER TABLE articles ADD COLUMN share_count INTEGER")
            logger.info("✅ 已添加 share_count 字段")
        except Exception as e:
            conn.rollback()
            logger.warning(f"检查 share_count 字段时出错: {e}")
        
        # 检查并添加 local_html_path 字段
        try:
            cursor.execute("SELECT local_html_path FROM articles LIMIT 1")
            logger.info("✅ local_html_path 字段已存在")
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()  # 回滚失败的查询
            logger.info("添加 local_html_path 字段...")
            cursor.execute("ALTER TABLE articles ADD COLUMN local_html_path TEXT")
            logger.info("✅ 已添加 local_html_path 字段")
        except Exception as e:
            conn.rollback()
            logger.warning(f"检查 local_html_path 字段时出错: {e}")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✅ 数据库迁移完成！")
        logger.info("\n字段说明：")
        logger.info("  - read_count: 阅读量")
        logger.info("  - old_like_count: 点赞数（大拇指👍）")
        logger.info("  - like_count: 喜欢数/收藏数（爱心❤️）")
        logger.info("  - share_count: 分享数")
        logger.info("  - comment_count: 评论数")
        logger.info("  - local_html_path: 本地HTML文件路径")
        
    except psycopg2.OperationalError as e:
        logger.error(f"❌ 无法连接到数据库: {e}")
        logger.error("请确保：")
        logger.error("  1. Docker 容器正在运行")
        logger.error("  2. PostgreSQL 服务已启动")
        logger.error("  3. 端口 5435 未被占用")
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    migrate_database()
