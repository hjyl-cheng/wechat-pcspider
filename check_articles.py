# coding: utf-8
"""
查询数据库中的文章数据
"""
from database import get_db_session
from models import Article
from sqlalchemy import desc

def check_articles():
    """查询最新的两篇文章"""
    with get_db_session() as session:
        articles = session.query(Article).order_by(desc(Article.fetched_at)).limit(2).all()
        
        print("\n" + "="*80)
        print("最新的两篇文章数据")
        print("="*80)
        
        for i, article in enumerate(articles, 1):
            print(f"\n【文章 {i}】")
            print(f"标题: {article.title}")
            print(f"发布日期: {article.publish_date}")
            print(f"抓取时间: {article.fetched_at}")
            print(f"阅读数: {article.read_count}")
            print(f"点赞数(👍): {article.old_like_count}")
            print(f"喜欢数/收藏数(❤️): {article.like_count}")
            print(f"分享数: {article.share_count}")
            print(f"评论数: {article.comment_count}")
            print(f"本地HTML: {article.local_html_path}")
            url_display = article.url[:80] + "..." if len(article.url) > 80 else article.url
            print(f"URL: {url_display}")
            print("-"*80)

if __name__ == '__main__':
    check_articles()
