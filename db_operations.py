# coding: utf-8
"""
数据库操作函数
提供账号、参数、文章的CRUD操作
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import and_, or_
from database import get_db_session
from models import Account, Parameter, Article
import logging
import re
logger = logging.getLogger(__name__)
def get_or_create_account(biz: str, name: str = None) -> Dict:
    """
    获取或创建公众号
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    name : str, optional
        公众号名称
    
    Returns
    -------
    dict
        公众号信息字典
    """
    with get_db_session() as session:
        account = session.query(Account).filter(Account.biz == biz).first()
        
        if not account:
            account = Account(biz=biz, name=name)
            session.add(account)
            session.flush()
            logger.info(f"✅ 创建新公众号: {biz} ({name})")
        elif name and account.name != name:
            account.name = name
            logger.info(f"✅ 更新公众号名称: {biz} -> {name}")
        
        # 返回字典而不是ORM对象
        return {
            'id': account.id,
            'biz': account.biz,
            'name': account.name
        }
def save_parameters(biz: str, params: Dict) -> Dict:
    """
    保存参数
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    params : dict
        参数字典，包含 cookie, key, pass_ticket, uin
    
    Returns
    -------
    dict
        参数信息字典
    """
    with get_db_session() as session:
        # 确保账号存在
        account = session.query(Account).filter(Account.biz == biz).first()
        if not account:
            account = Account(biz=biz)
            session.add(account)
            session.flush()
        
        # 提取 appmsg_token
        appmsg_token = None
        if 'cookie' in params:
            match = re.search(r'appmsg_token=([^;]+)', params['cookie'])
            if match:
                appmsg_token = match.group(1)
        
        # 使旧参数失效
        session.query(Parameter).filter(
            Parameter.biz == biz,
            Parameter.is_valid == True
        ).update({'is_valid': False})
        
        # 创建新参数
        parameter = Parameter(
            biz=biz,
            cookie=params.get('cookie', ''),
            key=params.get('key', ''),
            pass_ticket=params.get('pass_ticket', ''),
            uin=params.get('uin', ''),
            appmsg_token=appmsg_token,
            captured_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=4),  # 默认4小时过期
            is_valid=True
        )
        
        session.add(parameter)
        session.flush()
        
        logger.info(f"✅ 保存参数: {biz}")
        return {
            'id': parameter.id,
            'biz': parameter.biz,
            'is_valid': parameter.is_valid,
            'captured_at': parameter.captured_at
        }
def get_valid_parameters(biz: str) -> Optional[Dict]:
    """
    获取有效参数
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    
    Returns
    -------
    dict or None
        有效的参数字典，如果不存在返回None
    """
    with get_db_session() as session:
        parameter = session.query(Parameter).filter(
            Parameter.biz == biz,
            Parameter.is_valid == True,
            or_(
                Parameter.expires_at == None,
                Parameter.expires_at > datetime.now()
            )
        ).order_by(Parameter.captured_at.desc()).first()
        
        if parameter:
            logger.info(f"✅ 找到有效参数: {biz}")
            return {
                'cookie': parameter.cookie,
                'key': parameter.key,
                'pass_ticket': parameter.pass_ticket,
                'uin': parameter.uin,
                'appmsg_token': parameter.appmsg_token
            }
        else:
            logger.warning(f"⚠️  未找到有效参数: {biz}")
            return None
def invalidate_parameters(biz: str):
    """
    使参数失效
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    """
    with get_db_session() as session:
        count = session.query(Parameter).filter(
            Parameter.biz == biz,
            Parameter.is_valid == True
        ).update({'is_valid': False})
        
        logger.info(f"✅ 使{count}个参数失效: {biz}")
def save_article(article_data: Dict) -> Dict:
    """
    保存文章数据
    
    Parameters
    ----------
    article_data : dict
        文章数据字典
    
    Returns
    -------
    dict
        文章信息字典
    """
    with get_db_session() as session:
        # 检查文章是否已存在
        # 微信文章URL中的chksm等参数会变化，需要用核心参数匹配
        # 核心参数：__biz + mid + idx + sn
        logger.debug(f"查询文章: BIZ={article_data['biz']}, title={article_data.get('title')}, url={article_data['url'][:50] if article_data.get('url') else 'None'}...")
        
        # 提取URL核心参数
        def extract_core_params(url):
            """提取URL的核心参数 (biz, mid, idx, sn)"""
            if not url:
                return None
            import re
            params = {}
            # 提取__biz, mid, idx, sn
            for key in ['__biz', 'mid', 'idx', 'sn']:
                if key == '__biz':
                    pattern = r'__biz=([^&]+)'
                else:
                    pattern = rf'{key}=([^&]+)'
                match = re.search(pattern, url)
                if match:
                    params[key] = match.group(1)
            return params if len(params) >= 3 else None  # 至少要有3个参数
        
        new_params = extract_core_params(article_data['url'])
        
        # 先尝试精确URL匹配
        article = session.query(Article).filter(
            Article.biz == article_data['biz'],
            Article.url == article_data['url']
        ).first()
        
        # 如果没找到，尝试核心参数匹配
        if not article and new_params:
            existing_articles = session.query(Article).filter(
                Article.biz == article_data['biz']
            ).all()
            
            for existing in existing_articles:
                existing_params = extract_core_params(existing.url)
                if existing_params and all(
                    existing_params.get(k) == v for k, v in new_params.items()
                ):
                    article = existing
                    logger.debug(f"  通过核心参数匹配到文章: mid={new_params.get('mid')}")
                    break
        
        logger.debug(f"查询结果: {'找到现有文章' if article else '未找到,将创建新文章'}")
        
        if article:
            # 更新现有文章
            article.title = article_data.get('title') or article.title
            article.url = article_data.get('url') or article.url
            article.short_url = article_data.get('short_url') or article.short_url
            article.html_content = article_data.get('html_content') or article.html_content
            article.publish_date = article_data.get('publish_date') or article.publish_date
            article.read_count = article_data.get('read_count', article.read_count)
            article.old_like_count = article_data.get('old_like_count', article.old_like_count)
            article.like_count = article_data.get('like_count', article.like_count)
            article.share_count = article_data.get('share_count', article.share_count)
            article.comment_count = article_data.get('comment_count', article.comment_count)
            article.local_html_path = article_data.get('local_html_path') or article.local_html_path
            article.fetched_at = datetime.now()
            logger.info(f"✅ 更新文章: {article.title}")
        else:
            # 创建新文章
            article = Article(
                biz=article_data['biz'],
                url=article_data['url'],
                short_url=article_data.get('short_url'),
                title=article_data.get('title'),
                html_content=article_data.get('html_content'),
                publish_date=article_data.get('publish_date'),
                read_count=article_data.get('read_count'),
                old_like_count=article_data.get('old_like_count'),
                like_count=article_data.get('like_count'),
                share_count=article_data.get('share_count'),
                comment_count=article_data.get('comment_count'),
                local_html_path=article_data.get('local_html_path')
            )
            session.add(article)
            logger.info(f"✅ 保存新文章: {article.title}")
        
        session.flush()
        logger.debug(f"session.flush() 完成，准备返回")
        
        # 验证保存成功
        article_id = article.id
        logger.info(f"文章ID: {article_id}")
        
        # 在返回前再次查询确认
        verify = session.query(Article).filter(Article.id == article_id).first()
        if verify:
            logger.info(f"✓ 验证成功: 文章已在session中 (ID: {article_id})")
        else:
            logger.error(f"✗ 验证失败: 无法在session中找到刚保存的文章")
        
        # 尝试转换为字典，捕获可能的异常
        try:
            result = article.to_dict()
            logger.debug(f"✓ to_dict() 成功")
            return result
        except Exception as e:
            logger.error(f"✗ to_dict() 失败: {e}")
            import traceback
            traceback.print_exc()
            # 即使to_dict失败，也返回基本信息
            return {
                'id': article.id,
                'title': article.title,
                'biz': article.biz
            }
def get_article(url: str) -> Optional[Dict]:
    """
    根据URL获取文章（支持短链接和完整URL）
    
    Parameters
    ----------
    url : str
        文章URL（短链接或完整URL）
    
    Returns
    -------
    dict or None
        文章字典，如果不存在返回None
    """
    with get_db_session() as session:
        # 同时查找完整URL和短链接
        article = session.query(Article).filter(
            or_(
                Article.url == url,
                Article.short_url == url
            )
        ).first()
        return article.to_dict() if article else None
def get_articles_by_filters(
    biz: str,
    start_date: datetime = None,
    end_date: datetime = None,
    min_read_count: int = None
) -> List[Dict]:
    """
    根据过滤条件获取文章列表
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    start_date : datetime, optional
        开始日期
    end_date : datetime, optional
        结束日期
    min_read_count : int, optional
        最小阅读数
    
    Returns
    -------
    List[dict]
        文章字典列表
    """
    with get_db_session() as session:
        query = session.query(Article).filter(Article.biz == biz)
        
        # publish_date在数据库中是字符串，需要转换为字符串比较
        if start_date:
            start_date_str = start_date.strftime('%Y-%m-%d')
            query = query.filter(Article.publish_date >= start_date_str)
        
        if end_date:
            end_date_str = end_date.strftime('%Y-%m-%d')
            query = query.filter(Article.publish_date <= end_date_str)
        
        if min_read_count is not None:
            query = query.filter(Article.read_count >= min_read_count)
        
        articles = query.order_by(Article.publish_date.desc()).all()
        
        logger.info(f"✅ 查询到{len(articles)}篇文章")
        return [article.to_dict() for article in articles]
def is_article_fresh(url: str, max_age_hours: int = 24) -> bool:
    """
    检查文章数据是否新鲜（最近获取过）
    
    Parameters
    ----------
    url : str
        文章URL
    max_age_hours : int
        最大年龄（小时）
    
    Returns
    -------
    bool
        是否新鲜
    """
    article = get_article(url)
    if not article or not article.get('fetched_at'):
        return False
    
    # fetched_at 可能是字符串或datetime
    fetched_at = article.get('fetched_at')
    if isinstance(fetched_at, str):
        fetched_at = datetime.fromisoformat(fetched_at)
    
    age = datetime.now() - fetched_at
    is_fresh = age < timedelta(hours=max_age_hours)
    
    if is_fresh:
        logger.info(f"✅ 文章数据新鲜: {url[:50]}... (获取于 {fetched_at})")
    else:
        logger.info(f"⚠️  文章数据过期: {url[:50]}... (获取于 {fetched_at})")
    
    return is_fresh
