# coding: utf-8
"""
清空数据库中的所有文章数据
"""
from database import get_db_session
from models import Article
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_all_articles():
    """清空数据库中的所有文章"""
    
    try:
        with get_db_session() as session:
            # 先查询文章数量
            count = session.query(Article).count()
            
            if count == 0:
                logger.info("✅ 数据库中没有文章，无需清空")
                return
            
            logger.info(f"📊 数据库中共有 {count} 篇文章")
            
            # 确认操作
            print(f"\n⚠️  警告：即将删除数据库中的所有 {count} 篇文章！")
            print("   此操作不可恢复！")
            confirm = input("\n是否继续？(输入 'yes' 确认): ")
            
            if confirm.lower() != 'yes':
                logger.info("❌ 操作已取消")
                return
            
            # 删除所有文章
            logger.info("🗑️  正在删除文章...")
            deleted = session.query(Article).delete()
            session.commit()
            
            logger.info(f"✅ 成功删除 {deleted} 篇文章")
            
            # 验证
            remaining = session.query(Article).count()
            if remaining == 0:
                logger.info("✅ 数据库已清空")
            else:
                logger.warning(f"⚠️  还剩余 {remaining} 篇文章")
                
    except Exception as e:
        logger.error(f"❌ 清空失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    clear_all_articles()
