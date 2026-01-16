# coding: utf-8
"""
显示数据库中所有文章的日期分布
"""
from database import get_db_session
from models import Article, Account
from sqlalchemy import func

with get_db_session() as session:
    print("\n" + "="*80)
    print("数据库中的文章日期分布")
    print("="*80)
    
    # 按公众号和日期统计
    results = session.query(
        Account.name,
        Article.biz,
        Article.publish_date,
        func.count(Article.id).label('count')
    ).join(Account, Article.biz == Account.biz)\
     .group_by(Account.name, Article.biz, Article.publish_date)\
     .order_by(Account.name, Article.publish_date.desc())\
     .all()
    
    current_account = None
    for name, biz, date, count in results:
        if name != current_account:
            if current_account is not None:
                print()
            print(f"\n【{name}】(BIZ: {biz})")
            current_account = name
        print(f"  {date}: {count}篇")
    
    print("\n" + "="*80)
