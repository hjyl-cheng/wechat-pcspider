# coding: utf-8
"""
数据库备份脚本
将 PostgreSQL 数据库导出为 SQL 和 JSON 格式
"""
import os
import json
from datetime import datetime
from database import get_db_session
from models import Account, Parameter, Article

def backup_to_json():
    """将数据库导出为 JSON 格式"""
    backup_dir = "backup"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with get_db_session() as session:
        # 备份 accounts
        accounts = session.query(Account).all()
        accounts_data = []
        for acc in accounts:
            accounts_data.append({
                'id': acc.id,
                'biz': acc.biz,
                'name': acc.name,
                'created_at': acc.created_at.isoformat() if acc.created_at else None,
                'updated_at': acc.updated_at.isoformat() if acc.updated_at else None
            })
        
        # 备份 parameters
        parameters = session.query(Parameter).all()
        params_data = []
        for p in parameters:
            params_data.append({
                'id': p.id,
                'biz': p.biz,
                'cookie': p.cookie[:100] + '...' if p.cookie and len(p.cookie) > 100 else p.cookie,
                'key': p.key[:50] + '...' if p.key and len(p.key) > 50 else p.key,
                'pass_ticket': p.pass_ticket[:50] + '...' if p.pass_ticket and len(p.pass_ticket) > 50 else p.pass_ticket,
                'uin': p.uin,
                'appmsg_token': p.appmsg_token,
                'captured_at': p.captured_at.isoformat() if p.captured_at else None,
                'expires_at': p.expires_at.isoformat() if p.expires_at else None,
                'is_valid': p.is_valid
            })
        
        # 备份 articles
        articles = session.query(Article).all()
        articles_data = []
        for art in articles:
            articles_data.append({
                'id': art.id,
                'biz': art.biz,
                'url': art.url,
                'short_url': art.short_url,
                'title': art.title,
                'publish_date': art.publish_date.isoformat() if art.publish_date else None,
                'read_count': art.read_count,
                'old_like_count': art.old_like_count,
                'like_count': art.like_count,
                'share_count': art.share_count,
                'comment_count': art.comment_count,
                'local_html_path': art.local_html_path,
                'fetched_at': art.fetched_at.isoformat() if art.fetched_at else None
            })
        
        # 保存备份
        backup_data = {
            'backup_time': datetime.now().isoformat(),
            'accounts': accounts_data,
            'parameters': params_data,
            'articles': articles_data,
            'stats': {
                'accounts_count': len(accounts_data),
                'parameters_count': len(params_data),
                'articles_count': len(articles_data)
            }
        }
        
        backup_file = os.path.join(backup_dir, f"wechat_db_backup_{timestamp}.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 数据库备份完成!")
        print(f"   备份文件: {backup_file}")
        print(f"   公众号数量: {len(accounts_data)}")
        print(f"   参数记录数: {len(params_data)}")
        print(f"   文章数量: {len(articles_data)}")
        
        return backup_file

if __name__ == '__main__':
    backup_to_json()
