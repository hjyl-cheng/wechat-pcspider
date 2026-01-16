# coding: utf-8
"""
检查日期查询问题
"""
from database import get_db_session
from models import Article
from sqlalchemy import func

with get_db_session() as session:
    # 查看所有文章的发布日期
    print("\n=== 数据库中的文章发布日期统计 ===")
    dates = session.query(
        Article.publish_date, 
        func.count(Article.id)
    ).group_by(Article.publish_date).order_by(Article.publish_date.desc()).all()
    
    for date, count in dates:
        print(f"{date}: {count}篇")
    
    # 查看所有 BIZ
    print("\n=== 数据库中的 BIZ 统计 ===")
    bizs = session.query(
        Article.biz,
        func.count(Article.id)
    ).group_by(Article.biz).all()
    
    for biz, count in bizs:
        print(f"{biz}: {count}篇")
    
    # 测试查询 2025-12-01
    print("\n=== 查询 2025-12-01 的文章 ===")
    articles = session.query(Article).filter(
        Article.publish_date == '2025-12-01'
    ).all()
    print(f"找到 {len(articles)} 篇文章")
    
    # 测试查询 2025-11-29
    print("\n=== 查询 2025-11-29 的文章 ===")
    articles = session.query(Article).filter(
        Article.publish_date == '2025-11-29'
    ).all()
    print(f"找到 {len(articles)} 篇文章")
    for article in articles:
        print(f"  - {article.title} (BIZ: {article.biz})")
