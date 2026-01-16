# coding: utf-8
"""
数据库连接和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging
logger = logging.getLogger(__name__)
# 数据库配置
DATABASE_URL = "postgresql://wechat:wechat123@localhost:5435/wechat_articles"
# 创建引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 自动检测连接是否有效
    echo=False  # 生产环境设为False
)
# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 创建基类
Base = declarative_base()
@contextmanager
def get_db_session():
    """
    获取数据库会话的上下文管理器
    
    使用方法:
        with get_db_session() as session:
            # 数据库操作
            pass
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("✓ 数据库事务已提交")
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        session.close()
def init_db():
    """初始化数据库（创建所有表）"""
    from models import Account, Parameter, Article
    Base.metadata.create_all(bind=engine)
    logger.info("✅ 数据库表已创建")
def test_connection():
    """测试数据库连接"""
    try:
        from sqlalchemy import text
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False