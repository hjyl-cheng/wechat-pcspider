# coding: utf-8
"""
新的API端点实现（使用数据库缓存）
这个文件包含重构后的API端点，将逐步替换api_server.py中的旧实现
"""
from flask import request, jsonify
from datetime import datetime, timedelta
import logging
import re
import json
import requests
import time
import os
# 导入数据库操作
from db_operations import (
    get_or_create_account,
    save_parameters,
    get_valid_parameters,
    invalidate_parameters,
    save_article,
    get_article,
    get_articles_by_filters,
    is_article_fresh
)
from db_helpers import get_biz_by_account_name
# 导入现有功能
from smart_batch_fetch import (
    extract_appmsg_token_from_cookie,
    extract_biz_from_url,
)
from download_full_html import download_full_html_with_stats
from wechatarticles import ArticlesInfo
logger = logging.getLogger(__name__)


def _write_params_to_config(params):
    """
    将数据库参数写入params/new_wechat_config.py
    这样download_full_html.py就能读取到正确的参数
    
    Parameters
    ----------
    params : dict
        数据库中的参数，包含 cookie, key, pass_ticket, uin 等
    """
    from datetime import datetime
    
    # 数据库参数是小写的，需要转换为大写
    config_content = f'''# coding: utf-8
# 由api_endpoints_new.py自动生成
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

COOKIE = '{params.get('cookie', '')}'

KEY = '{params.get('key', '')}'

PASS_TICKET = '{params.get('pass_ticket', '')}'

UIN = '{params.get('uin', '')}'

DEVICETYPE = 'UnifiedPCWindows'

CLIENTVERSION = ''

BIZ = ''
'''
    
    with open('params/new_wechat_config.py', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    # 重新加载模块，确保下次导入时使用新参数
    import importlib
    import params.new_wechat_config
    importlib.reload(params.new_wechat_config)
    
    logger.info(f"   ✅ 已更新params/new_wechat_config.py")
def fetch_articles_with_params(biz, params, start_date=None, end_date=None, should_stop_func=None):
    """
    使用数据库参数获取公众号文章列表（支持增量更新）
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    params : dict
        数据库中的参数
    start_date : datetime, optional
        开始日期
    end_date : datetime, optional
        结束日期
    should_stop_func : function, optional
        回调函数，接收 article 字典，返回 True 则停止获取
    
    Returns
    -------
    list
        文章列表
    """
    logger.info(f"📡 使用数据库参数获取文章列表...")
    
    # 构造请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 MicroMessenger/3.4.0',
        'Cookie': params['cookie'],
        'Referer': f'https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={biz}&scene=124',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    all_articles = []
    offset = 0
    count = 10
    has_more = True
    
    while has_more:
        # ... (API URL construction) ...
        api_url = (
            f"https://mp.weixin.qq.com/mp/profile_ext?"
            f"action=getmsg&"
            f"__biz={biz}&"
            f"f=json&"
            f"offset={offset}&"
            f"count={count}&"
            f"is_ok=1&"
            f"scene=124&"
            f"uin={params.get('uin', '')}&"
            f"key={params.get('key', '')}&"
            f"pass_ticket={params.get('pass_ticket', '')}&"
            f"wxtoken=&"
            f"appmsg_token={params.get('appmsg_token', '')}&"
            f"x5=0"
        )
        
        try:
            logger.info(f"   获取第 {offset//count + 1} 页...")
            
            response = requests.get(api_url, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('ret') != 0:
                # Error handling...
                errmsg = data.get('errmsg', 'Unknown')
                if 'no session' in errmsg.lower():
                    return {'error': 'no_session', 'message': '参数已失效'}
                logger.warning(f"   ⚠️  API返回错误: {errmsg}")
                break
            
            # 解析文章列表
            general_msg_list = data.get('general_msg_list', {})
            if isinstance(general_msg_list, str):
                general_msg_list = json.loads(general_msg_list)
            
            msg_list = general_msg_list.get('list', [])
            
            if not msg_list:
                logger.info(f"   ✅ 已获取所有文章")
                break
            
            # 处理每条消息
            for msg in msg_list:
                comm_msg_info = msg.get('comm_msg_info', {})
                app_msg_ext_info = msg.get('app_msg_ext_info', {})
                
                if not app_msg_ext_info:
                    continue
                
                publish_time = comm_msg_info.get('datetime', 0)
                article_date = datetime.fromtimestamp(publish_time)
                
                # 检查日期范围
                if end_date and article_date > end_date + timedelta(days=1):
                    # 文章太新，跳过，继续找旧的
                    continue
                
                if start_date and article_date < start_date:
                    # 文章太旧，结束获取
                    logger.info(f"   🛑 遇到早于开始日期的文章 ({article_date.date()})，停止获取")
                    has_more = False
                    break
                
                # 主文章
                article_url = app_msg_ext_info.get('content_url', '').replace('\\/', '/')
                article_title = app_msg_ext_info.get('title', '')
                
                article = {
                    'title': article_title,
                    'url': article_url,
                    'digest': app_msg_ext_info.get('digest', ''),
                    'cover': app_msg_ext_info.get('cover', ''),
                    'publish_time': publish_time,
                    'publish_date': article_date.strftime('%Y-%m-%d'),
                }
                
                # 检查主文章是否已存在
                main_article_exists = should_stop_func and should_stop_func(article) if should_stop_func else False
                
                if article['url'] and not main_article_exists:
                    all_articles.append(article)
                
                # 多图文消息（即使主文章存在，也要处理多图文）
                multi_app_msg_item_list = app_msg_ext_info.get('multi_app_msg_item_list', [])
                if multi_app_msg_item_list:
                    logger.info(f"   📑 发现 {len(multi_app_msg_item_list)} 篇多图文")
                for item in multi_app_msg_item_list:
                    sub_article = {
                        'title': item.get('title', ''),
                        'url': item.get('content_url', '').replace('\\/', '/'),
                        'digest': item.get('digest', ''),
                        'cover': item.get('cover', ''),
                        'publish_time': publish_time,
                        'publish_date': article_date.strftime('%Y-%m-%d'),
                    }
                    if sub_article['url']:
                        # 检查子文章是否已存在
                        sub_exists = should_stop_func and should_stop_func(sub_article) if should_stop_func else False
                        if not sub_exists:
                            all_articles.append(sub_article)
                
                # 如果主文章已存在，且所有子文章也都存在，则停止获取
                if main_article_exists:
                    logger.info(f"   🛑 遇到已存在的文章，停止获取: {article_title}")
                    has_more = False
                    break
            
            offset += count
            time.sleep(1 + (offset % 3)) # 随机延迟
            
        except Exception as e:
            logger.error(f"   ❌ 获取失败: {e}")
            break
    
    logger.info(f"✅ 从API新获取 {len(all_articles)} 篇文章")
    
    # 调试：打印每篇文章的URL
    for idx, art in enumerate(all_articles, 1):
        logger.debug(f"  [{idx}] {art.get('title', '')[:40]}: {art.get('url', '')[:100]}")
    
    return all_articles
def fetch_article_with_cache():
    """
    获取单篇文章数据（使用数据库缓存）
    
    流程：
    1. 提取BIZ
    2. 检查数据库缓存
    3. 如果缓存新鲜（<24小时）→ 返回缓存
    4. 否则 → 检查参数 → 调用微信API → 存储到数据库 → 返回
    """
    try:
        # 解析请求
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        account_name = data.get('account_name')
        article_url = data.get('article_url')
        
        if not article_url:
            return jsonify({'success': False, 'error': '缺少必需参数: article_url'}), 400
        
        logger.info(f"📥 收到请求: 公众号={account_name}, URL={article_url}")
        
        # 1. 获取BIZ和参数（优先从数据库）
        biz = None
        params = None
        
        # 方法1：如果提供了account_name，从数据库查询BIZ和参数
        if account_name:
            biz, params = get_biz_by_account_name(account_name)
            if biz:
                logger.info(f"✅ 从数据库获取BIZ: {biz} (账号: {account_name})")
                if params:
                    logger.info(f"   同时获取到参数 (Cookie长度: {len(params.get('cookie', ''))})")
        
        # 方法2：从URL提取BIZ（如果方法1没获取到）
        if not biz:
            logger.info(f"   从URL提取BIZ...")
            biz = extract_biz_from_url(article_url)
            if not biz:
                error_msg = '无法从URL提取BIZ'
                if 'wappoc_appmsgcaptcha' in article_url or 'captcha' in article_url.lower():
                    error_msg = '该文章需要验证码，请尝试：1) 更换其他文章URL，2) 在微信PC端手动打开文章后重试'
                else:
                    error_msg = '无法从URL提取BIZ，请检查URL格式或尝试其他文章'
                
                logger.error(f"❌ {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 400
            
            logger.info(f"✅ 从URL提取BIZ: {biz}")
            
            # 提取到BIZ后，尝试获取参数
            if not params:
                params = get_valid_parameters(biz)
                if params:
                    logger.info(f"   获取到已存储的参数")
        
        # 更新账号信息
        get_or_create_account(biz, account_name)
        
        # 2. 检查文章数据缓存
        cached_article = get_article(article_url)
        if cached_article and is_article_fresh(article_url, max_age_hours=24):
            logger.info(f"✅ 使用缓存的文章数据: {cached_article.get('title')}")
            return jsonify({
                'success': True,
                'data': {
                    'account_name': account_name,
                    'biz': biz,
                    'from_cache': True,
                    **cached_article
                }
            })
        
        # 3. 没有缓存或缓存过期，需要从微信API获取
        logger.info(f"📡 文章数据未缓存，从微信API获取...")
        
        # 3.1 确保有参数
        if not params:
            # 参数不存在，需要捕获
            logger.info(f"⚠️  数据库中没有参数，开始自动捕获...")
            
            from api_server import ProxyManager
            if not ProxyManager.start_proxy_and_capture(article_url, biz=biz, timeout=120):
                return jsonify({
                    'success': False,
                    'error': '参数捕获失败，请确保微信已正常运行'
                }), 500
            
            # 等待一下确保数据库更新
            time.sleep(2)
            
            # 重新获取参数
            params = get_valid_parameters(biz)
            if not params:
                return jsonify({
                    'success': False,
                    'error': '参数捕获后仍无法从数据库获取'
                }), 500
        
        logger.info(f"✅ 使用参数 (Cookie长度: {len(params.get('cookie', ''))})")
        
        # 3.2 转换短链接为长链接
        final_article_url = article_url
        if '/s/' in article_url and '__biz=' not in article_url:
            logger.info(f"   检测到短链接，正在转换...")
            try:
                import requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Cookie': params['cookie'],
                }
                response = requests.get(article_url, headers=headers, timeout=15)
                
                # 从页面内容提取完整URL
                patterns = [
                    r'var\s+msg_link\s*=\s*["\']([^"\']+)["\']',
                    r'url:\s*["\']([^"\']+/s\?[^"\']+)["\']',
                    r'window.msg_link = "([^"]+)"',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        extracted_url = match.group(1)
                        # 转换HTML实体
                        extracted_url = extracted_url.replace('&amp;', '&').replace('\\/', '/')
                        if '__biz=' in extracted_url and 'mid=' in extracted_url:
                            final_article_url = extracted_url
                            logger.info(f"   ✅ 转换成功: {final_article_url[:80]}...")
                            break
                else:
                    logger.warning(f"   ⚠️  无法从页面提取完整URL")
                    
            except Exception as e:
                logger.warning(f"   ⚠️  转换失败: {e}")
        
        # 3.3 调用微信API获取数据
        try:
            articles_info = ArticlesInfo(
                appmsg_token=params['appmsg_token'],
                cookie=params['cookie']
            )
            stats = get_article_stats(final_article_url, articles_info)
            
            if not stats or not stats.get('success'):
                error_msg = stats.get('error', '未知错误') if stats else '返回值为空'
                
                # 记录错误但不自动重新捕获（避免频繁捕获）
                logger.error(f"❌ 微信API返回错误: {error_msg}")
                
                # 如果是参数错误，提示用户可能需要重新捕获
                if 'params is error' in error_msg or 'no session' in error_msg:
                    # 注意：不立即标记失效，让用户决定
                    logger.warning(f"⚠️  可能参数已失效，建议重新捕获")
                    return jsonify({
                        'success': False,
                        'error': f'参数可能已失效: {error_msg}',
                        'need_recapture': True,
                        'biz': biz
                    }), 400
                else:
                    # 其他错误
                    return jsonify({
                        'success': False,
                        'error': f'获取文章数据失败: {error_msg}'
                    }), 500
            
            # 3.4 获取文章标题和HTML内容
            logger.info(f"   正在获取文章标题和内容...")
            article_title = None
            article_html = None
            try:
                import requests as req
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Cookie': params['cookie'],
                }
                article_response = req.get(final_article_url, headers=headers, timeout=15)
                article_html = article_response.text
                
                # 从HTML提取标题
                title_match = re.search(r'<h1[^>]*class="rich_media_title"[^>]*>([^<]+)</h1>', article_html)
                if title_match:
                    article_title = title_match.group(1).strip()
                else:
                    # 尝试其他方式
                    title_match2 = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', article_html)
                    if title_match2:
                        article_title = title_match2.group(1).strip()
                
                logger.info(f"   ✅ 获取到标题: {article_title}")
            except Exception as e:
                logger.warning(f"   ⚠️  获取文章内容失败: {e}")
            
            # 3.5 保存到数据库（包含完整数据）
            # 清理统计数据：将 "N/A" 或非数字值转换为 None
            def clean_stat(value):
                if value == "N/A" or value is None:
                    return None
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            
            article_data = {
                'biz': biz,
                'url': final_article_url,  # 保存完整URL
                'short_url': article_url,   # 保存短链接便于查找
                'title': article_title,
                'html_content': article_html,
                'publish_date': None,  # 暂不提取
                'read_count': clean_stat(stats.get('read_count')),
                'like_count': clean_stat(stats.get('like_count')),
                'comment_count': clean_stat(stats.get('comment_count'))
            }
            
            saved_article = save_article(article_data)
            
            logger.info(f"✅ 成功获取并保存文章数据: {saved_article.get('title')}")
            
            return jsonify({
                'success': True,
                'data': {
                    'account_name': account_name,
                    'biz': biz,
                    'from_cache': False,
                    **saved_article
                }
            })
            
        except Exception as e:
            logger.error(f"❌ 调用微信API失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'调用微信API失败: {str(e)}'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
def fetch_articles_filtered():
    """
    批量获取文章（带过滤）
    
    请求体：
    {
        "account_name": "公众号名称",
        "article_url": "任意一篇文章URL（用于提取BIZ）",
        "start_date": "2024-12-01",
        "end_date": "2024-12-10",
        "min_read_count": 10000,
        "limit": 10  // 可选，限制数量
    }
    """
    try:
        # 解析请求
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        account_name = data.get('account_name')
        article_url = data.get('article_url')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        min_read_count = data.get('min_read_count')
        limit = data.get('limit', 20)  # 默认限制20篇
        
        if not article_url:
            return jsonify({'success': False, 'error': '缺少必需参数: article_url'}), 400
        
        logger.info(f"📥 收到批量请求: 公众号={account_name}")
        
        # 1. 优先从URL提取BIZ（URL中的BIZ是最准确的）
        biz = extract_biz_from_url(article_url)
        if not biz:
            return jsonify({'success': False, 'error': '无法从URL提取BIZ'}), 400
        logger.info(f"✅ 从URL提取BIZ: {biz}")
        
        # 2. 获取该BIZ的参数
        params = get_valid_parameters(biz)
        
        # 创建或更新账号
        get_or_create_account(biz, account_name)
        
        # 2. 确保有参数（自动捕获）
        if not params:
            logger.info(f"⚠️  数据库中没有参数，开始自动捕获...")
            
            from api_server import ProxyManager
            if not ProxyManager.start_proxy_and_capture(article_url, biz=biz, timeout=120):
                return jsonify({
                    'success': False,
                    'error': '参数捕获失败，请确保微信已正常运行'
                }), 500
            
            time.sleep(2)
            
            params = get_valid_parameters(biz)
            if not params:
                return jsonify({
                    'success': False,
                    'error': '参数捕获后仍无法从数据库获取'
                }), 500
        
        # 3. 解析日期
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        
        # 4. 检查数据库中该日期范围内每一天是否都有数据
        from database import get_db_session
        from models import Article
        
        missing_dates = []
        if start_date and end_date:
            with get_db_session() as session:
                # 获取该BIZ在日期范围内所有文章的发布日期
                existing_articles = session.query(Article.publish_date).filter(
                    Article.biz == biz,
                    Article.publish_date >= start_date.strftime('%Y-%m-%d'),
                    Article.publish_date <= end_date.strftime('%Y-%m-%d')
                ).all()
                
                existing_dates = set()
                for row in existing_articles:
                    if row.publish_date:
                        # publish_date可能是字符串或datetime
                        if isinstance(row.publish_date, str):
                            existing_dates.add(row.publish_date)
                        else:
                            existing_dates.add(row.publish_date.strftime('%Y-%m-%d'))
                
                # 检查每一天是否都有数据
                current_date = start_date
                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    if date_str not in existing_dates:
                        missing_dates.append(date_str)
                    current_date += timedelta(days=1)
        
        if not missing_dates:
            # 所有日期都有数据，直接从数据库返回
            logger.info(f"📊 数据库中已有完整数据（{start_date_str} ~ {end_date_str}），直接返回")
            db_articles = get_articles_by_filters(biz, start_date, end_date, min_read_count)
            return jsonify({
                'success': True,
                'data': {
                    'account_name': account_name,
                    'biz': biz,
                    'from_cache': True,
                    'total_saved': 0,
                    'total': len(db_articles[:limit]),
                    'articles': db_articles[:limit]
                }
            })
        
        # 5. 有缺失日期，需要从API获取
        logger.info(f"📡 数据库缺失以下日期的数据: {', '.join(missing_dates)}")
        logger.info(f"   开始从微信API获取缺失数据...")
        
        # 获取现有文章指纹（用于增量更新判断）
        existing_titles = set()
        
        with get_db_session() as session:
            existing = session.query(Article.title).filter(Article.biz == biz).all()
            for row in existing:
                if row.title:
                    existing_titles.add(row.title)
        
        logger.info(f"📚 数据库中已有 {len(existing_titles)} 篇文章（全部历史）")
        
        # 定义停止抓取的回调函数
        def should_stop_fetch(article):
            # 如果标题已存在，说明接上历史数据了
            title = article.get('title', '')
            if title and title in existing_titles:
                return True
            return False
        # 5. 从微信API获取（增量模式）
        logger.info(f"📡 从微信API获取文章（增量模式）...")
        
        try:
            articles_info = ArticlesInfo(
                appmsg_token=params['appmsg_token'],
                cookie=params['cookie']
            )
            
            # 获取文章列表（使用数据库参数，传入回调）
            articles = fetch_articles_with_params(biz, params, start_date, end_date, should_stop_func=should_stop_fetch)
            # 检查是否需要重新捕获
            if isinstance(articles, dict) and articles.get('error') == 'no_session':
                logger.warning(f"⚠️  参数已失效，开始重新捕获...")
                
                # 标记参数失效
                invalidate_parameters(biz)
                
                # 触发重新捕获
                from api_server import ProxyManager
                if ProxyManager.start_proxy_and_capture(article_url, biz=biz, timeout=120):
                    time.sleep(2)
                    
                    # 重新获取参数
                    params = get_valid_parameters(biz)
                    if params:
                        # 重试获取文章列表
                        articles = fetch_articles_with_params(biz, params, start_date, end_date, should_stop_func=should_stop_fetch)
                        
                        if isinstance(articles, dict) and articles.get('error'):
                            return jsonify({
                                'success': False,
                                'error': '重新捕获后仍然无法获取文章列表'
                            }), 500
                    else:
                        return jsonify({
                            'success': False,
                            'error': '参数重新捕获失败'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': '参数捕获失败，请确保微信已正常运行',
                        'need_recapture': True
                    }), 500
                    
                # 重新创建 ArticlesInfo
                articles_info = ArticlesInfo(
                    appmsg_token=params['appmsg_token'],
                    cookie=params['cookie']
                )
            
            # 如果有新文章，获取详情并保存
            new_articles_count = 0
            if articles and not (isinstance(articles, dict) and articles.get('error')):
                logger.info(f"   发现 {len(articles)} 篇新文章，开始获取详情...")
                new_articles_count = len(articles)
                
                # ✅ 关键：将数据库参数写入new_wechat_config.py，供download_full_html使用
                _write_params_to_config(params)
                
                # 批量获取统计数据并保存
                import requests as req
                
                for i, article in enumerate(articles, 1):
                    try:
                        article_url_item = article.get('url', '')
                        article_title = article.get('title', '')
                        
                        logger.info(f"   [{i}/{len(articles)}] 处理: {article_title[:30]}...")
                        
                        # 转换短链接（如果需要）
                        final_url = article_url_item
                        if '//mp.weixin.qq.com/s?' not in article_url_item and '//mp.weixin.qq.com/s/' in article_url_item:
                            try:
                                resp = req.get(article_url_item, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=False, timeout=10)
                                if resp.status_code in [301, 302]:
                                    loc = resp.headers.get('Location')
                                    if loc:
                                        final_url = loc
                                else:
                                    # 尝试从HTML中提取
                                    resp = req.get(article_url_item, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                                    content = resp.text
                                    urls = re.findall(r'var\s+msg_link\s*=\s*"([^"]+)"', content)
                                    if urls:
                                        final_url = urls[0].replace('\\/', '/')
                            except:
                                pass
                        
                        # 解码HTML实体 (&amp; -> &) - 必须在获取统计数据之前！
                        import html
                        final_url = html.unescape(final_url) if final_url else final_url
                        article_url_item = html.unescape(article_url_item) if article_url_item else article_url_item
                        
                        # ✅ 使用download_full_html_with_stats下载HTML并提取统计数据
                        logger.info(f"      📊 正在下载完整HTML并提取统计数据...")
                        logger.info(f"         URL: {final_url[:100]}...")
                        
                        download_result = download_full_html_with_stats(
                            final_url,
                            article_title,
                            article.get('publish_date'),
                            account_name=account_name,
                            output_dir="articles_html"
                        )
                        
                        html_file_path = download_result.get('filepath', '')
                        stats = download_result.get('stats', {})
                        
                        # 详细记录统计数据响应
                        if stats:
                            logger.info(f"      📊 从HTML提取的统计数据:")
                            logger.info(f"         read_num: {stats.get('read_num')}")
                            logger.info(f"         old_like_count: {stats.get('old_like_count')}")
                            logger.info(f"         like_count: {stats.get('like_count')}")
                            logger.info(f"         share_count: {stats.get('share_count')}")
                            logger.info(f"         comment_count: {stats.get('comment_count')}")
                        else:
                            logger.warning(f"      ⚠️  未能从HTML提取统计数据")
                        
                        # ✅ 获取留言并注入到HTML
                        if html_file_path and os.path.exists(html_file_path):
                            try:
                                logger.info(f"      💬 正在获取留言...")
                                from get_comments_improved import get_comment_id_from_html
                                from inject_comments_dom import inject_comments_direct_render
                                import urllib.parse
                                
                                # 1. 从已下载的HTML中提取comment_id
                                with open(html_file_path, 'r', encoding='utf-8') as f:
                                    downloaded_html = f.read()
                                
                                comment_id = get_comment_id_from_html(downloaded_html)
                                
                                if comment_id:
                                    # 2. 提取URL参数
                                    parsed = urllib.parse.urlparse(final_url)
                                    url_params = urllib.parse.parse_qs(parsed.query)
                                    __biz = url_params.get('__biz', [''])[0]
                                    idx = url_params.get('idx', ['1'])[0]
                                    
                                    # 3. 构建留言API请求
                                    comment_api_params = {
                                        'action': 'getcomment',
                                        '__biz': __biz,
                                        'idx': idx,
                                        'comment_id': comment_id,
                                        'limit': '100',
                                        'uin': params.get('uin', ''),
                                        'key': params.get('key', ''),
                                        'pass_ticket': params.get('pass_ticket', ''),
                                        'appmsg_token': params.get('appmsg_token', '')
                                    }
                                    
                                    comment_url = "https://mp.weixin.qq.com/mp/appmsg_comment?" + urllib.parse.urlencode(comment_api_params)
                                    
                                    headers = {
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                        'Cookie': params.get('cookie', '')
                                    }
                                    
                                    proxies = {"http": None, "https": None}
                                    comment_response = requests.get(comment_url, headers=headers, proxies=proxies, timeout=15)
                                    
                                    if comment_response.status_code == 200 and comment_response.text.strip():
                                        try:
                                            comments_data = comment_response.json()
                                            if comments_data and comments_data.get('elected_comment'):
                                                inject_comments_direct_render(html_file_path, comments_data)
                                            else:
                                                logger.info(f"      ℹ️  该文章没有精选留言")
                                        except:
                                            logger.info(f"      ℹ️  留言API返回非JSON格式")
                                    else:
                                        logger.info(f"      ℹ️  留言API请求失败")
                                else:
                                    logger.info(f"      ℹ️  该文章未开启留言功能")
                            except Exception as e:
                                logger.warning(f"      ⚠️  留言获取/注入失败: {e}")
                        
                        # 读取本地HTML文件（包含已注入的留言）
                        html_content = None
                        if html_file_path and os.path.exists(html_file_path):
                            try:
                                with open(html_file_path, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                logger.info(f"      ✅ HTML已下载 ({len(html_content)} 字节)")
                            except Exception as e:
                                logger.warning(f"      ⚠️  读取HTML文件失败: {e}")
                        else:
                            logger.warning(f"      ⚠️  HTML下载失败")
                        
                        # 从HTML提取标题（如果需要）
                        if html_content and not article_title:
                            import re
                            title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_content)
                            if title_match:
                                article_title = title_match.group(1).strip()
                        
                        # 清理统计数据：将空值转换为None
                        def clean_stat(value):
                            if value is None or value == '' or value == 'N/A':
                                return None
                            try:
                                return int(value)
                            except (ValueError, TypeError):
                                return None
                        
                        article_data = {
                            'biz': biz,
                            'url': final_url,
                            'short_url': article_url_item if article_url_item != final_url else None,
                            'title': article_title,
                            'html_content': html_content,
                            'publish_date': article.get('publish_date'),
                            'read_count': clean_stat(stats.get('read_num')),
                            'old_like_count': clean_stat(stats.get('old_like_count')),
                            'like_count': clean_stat(stats.get('like_count')),
                            'share_count': clean_stat(stats.get('share_count')),
                            'comment_count': clean_stat(stats.get('comment_count')),
                            'local_html_path': html_file_path
                        }
                        
                        # 直接插入新文章（前面的增量逻辑已经保证了只获取新文章）
                        logger.info(f"      准备保存:")
                        logger.info(f"        标题: {article_title}")
                        logger.info(f"        URL: {final_url}")  # 完整URL
                        logger.info(f"        短URL: {article_url_item if article_url_item else 'None'}")  # 完整短URL
                        
                        from database import get_db_session
                        from models import Article as ArticleModel
                        
                        with get_db_session() as db_session:
                            new_article = ArticleModel(
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
                            db_session.add(new_article)
                            db_session.flush()
                            logger.info(f"      ✅ 保存成功 (ID: {new_article.id})")



                        
                        # 避免请求过快（参考smart_batch_auto.py）
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.warning(f"   ⚠️  处理文章失败: {e}")
                        continue
            
            if new_articles_count > 0:
                logger.info(f"✅ 成功获取并保存 {new_articles_count} 篇新文章")
            else:
                logger.info(f"✅ 没有发现新文章（已全部覆盖）")
            
            # 6. 从数据库查询最终结果（按过滤条件）
            # 注意：这里重新查询以获取包括旧文章在内的所有符合条件的文章
            final_articles = get_articles_by_filters(biz, start_date, end_date, min_read_count)
            
            # 手动截取 limit（因为 get_articles_by_filters 没有 limit 参数）
            final_articles = final_articles[:limit]
            
            return jsonify({
                'success': True,
                'data': {
                    'account_name': account_name,
                    'biz': biz,
                    'from_cache': new_articles_count == 0, # 如果没有新文章，说明完全来自缓存
                    'total_saved': new_articles_count, # 本次新保存的数量
                    'total': len(final_articles),     # 返回给前端的总数
                    'articles': final_articles
                }
            })
            
        except Exception as e:
            logger.error(f"❌ 调用微信API失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'调用微信API失败: {str(e)}'
            }), 500
    
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500