# coding: utf-8
"""
数据库迁移脚本
添加新字段：old_like_count, share_count, local_html_path
"""
import sqlite3
import os

def migrate_database():
    """迁移数据库，添加新字段"""
    db_path = 'wechat_articles.db'
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，无需迁移")
        return
    
    print(f"开始迁移数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查并添加 old_like_count 字段
    try:
        cursor.execute("SELECT old_like_count FROM articles LIMIT 1")
        print("✅ old_like_count 字段已存在")
    except sqlite3.OperationalError:
        print("添加 old_like_count 字段...")
        cursor.execute("ALTER TABLE articles ADD COLUMN old_like_count INTEGER")
        print("✅ 已添加 old_like_count 字段")
    
    # 检查并添加 share_count 字段
    try:
        cursor.execute("SELECT share_count FROM articles LIMIT 1")
        print("✅ share_count 字段已存在")
    except sqlite3.OperationalError:
        print("添加 share_count 字段...")
        cursor.execute("ALTER TABLE articles ADD COLUMN share_count INTEGER")
        print("✅ 已添加 share_count 字段")
    
    # 检查并添加 local_html_path 字段
    try:
        cursor.execute("SELECT local_html_path FROM articles LIMIT 1")
        print("✅ local_html_path 字段已存在")
    except sqlite3.OperationalError:
        print("添加 local_html_path 字段...")
        cursor.execute("ALTER TABLE articles ADD COLUMN local_html_path TEXT")
        print("✅ 已添加 local_html_path 字段")
    
    conn.commit()
    conn.close()
    
    print("\n✅ 数据库迁移完成！")
    print("\n字段说明：")
    print("  - read_count: 阅读量")
    print("  - old_like_count: 点赞数（大拇指👍）")
    print("  - like_count: 喜欢数/收藏数（爱心❤️）")
    print("  - share_count: 分享数")
    print("  - comment_count: 评论数")
    print("  - local_html_path: 本地HTML文件路径")

if __name__ == '__main__':
    migrate_database()
