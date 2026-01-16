# coding: utf-8
"""
删除 favorite_count 字段（与 like_count 重复）
"""
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def remove_favorite_count():
    """删除 favorite_count 字段"""
    
    # Docker 容器中的 PostgreSQL 连接信息
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5435,
        'database': 'wechat_articles',
        'user': 'wechat',
        'password': 'wechat123'
    }
    
    logger.info(f"开始删除 favorite_count 字段...")
    logger.info(f"连接信息: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    try:
        # 连接数据库
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info(f"✅ 已连接到数据库: {DB_CONFIG['database']}")
        
        # 检查字段是否存在
        try:
            cursor.execute("SELECT favorite_count FROM articles LIMIT 1")
            logger.info("找到 favorite_count 字段，准备删除...")
            
            # 删除字段
            cursor.execute("ALTER TABLE articles DROP COLUMN favorite_count")
            logger.info("✅ 已删除 favorite_count 字段")
            
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()
            logger.info("✅ favorite_count 字段不存在，无需删除")
        except Exception as e:
            conn.rollback()
            logger.warning(f"检查或删除字段时出错: {e}")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✅ 数据库清理完成！")
        logger.info("\n当前字段说明：")
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
        logger.error(f"❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    remove_favorite_count()
