# coding: utf-8
"""
智能API端点（完全模拟smart_batch_auto.py的工作流程）

工作流程：
1. 参数保存到本地文件（BIZ专属）
2. 检查参数有效性，失效时自动重新捕获
3. 使用本地文件参数
4. 下载 HTML、获取统计数据
5. 保存为 JSON 和 CSV
6. 最后上传到数据库
"""

from flask import request, jsonify
from datetime import datetime, timedelta
import logging
import os
import sys
import re
import json
import time
import importlib.util

# 导入现有功能
from smart_batch_fetch import (
    extract_appmsg_token_from_cookie,
    extract_biz_from_url,
    save_to_csv,
    save_to_json
)
from download_full_html import download_full_html_with_stats
from extract_stats_from_html import extract_stats_from_html
from wechatarticles import ArticlesInfo
from db_operations import (
    get_or_create_account,
    save_article
)

logger = logging.getLogger(__name__)


def _write_params_to_config(biz_params):
    """
    将BIZ参数写入params/new_wechat_config.py
    这样download_full_html.py就能读取到正确的参数
    """
    from datetime import datetime
    
    config_content = f'''# coding: utf-8
# 由api_endpoints_smart.py自动生成
# BIZ: {biz_params.get('BIZ', '')}
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

COOKIE = '{biz_params.get('COOKIE', '')}'

KEY = '{biz_params.get('KEY', '')}'

PASS_TICKET = '{biz_params.get('PASS_TICKET', '')}'

UIN = '{biz_params.get('UIN', '')}'

DEVICETYPE = '{biz_params.get('DEVICETYPE', 'UnifiedPCWindows')}'

CLIENTVERSION = '{biz_params.get('CLIENTVERSION', '')}'

BIZ = '{biz_params.get('BIZ', '')}'
'''
    
    with open('params/new_wechat_config.py', 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    # 重新加载模块
    import importlib
    import params.new_wechat_config
    importlib.reload(params.new_wechat_config)
    
    logger.info(f"   ✅ 已更新params/new_wechat_config.py")


def check_params_validity(biz, biz_params):
    """
    检查参数是否有效
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    biz_params : dict
        BIZ参数
    
    Returns
    -------
    bool
        True表示有效，False表示失效
    """
    try:
        logger.info(f"🔍 检查参数有效性...")
        
        # 提取appmsg_token
        appmsg_token = extract_appmsg_token_from_cookie(biz_params['COOKIE'])
        if not appmsg_token:
            logger.warning(f"   ⚠️  无法提取appmsg_token")
            return False
        
        # 测试API调用
        import requests
        test_url = (
            f"https://mp.weixin.qq.com/mp/profile_ext?"
            f"action=getmsg&"
            f"__biz={biz}&"
            f"f=json&"
            f"offset=0&"
            f"count=1&"
            f"is_ok=1&"
            f"scene=124&"
            f"uin={biz_params['UIN']}&"
            f"key={biz_params['KEY']}&"
            f"pass_ticket={biz_params['PASS_TICKET']}&"
            f"wxtoken=&"
            f"appmsg_token={appmsg_token}&"
            f"x5=0"
        )
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': biz_params['COOKIE'],
            'Referer': f'https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={biz}&scene=124',
        }
        
        response = requests.get(test_url, headers=headers, timeout=10)
        data = response.json()
        
        ret = data.get('ret')
        errmsg = data.get('errmsg', '')
        
        if ret == -3 or 'no session' in errmsg.lower():
            logger.warning(f"   ❌ 参数已失效: {errmsg}")
            return False
        elif ret != 0:
            logger.warning(f"   ⚠️  API返回错误: {errmsg}")
            return False
        
        logger.info(f"   ✅ 参数有效")
        return True
        
    except Exception as e:
        logger.error(f"   ❌ 检查失败: {e}")
        return False


def load_biz_params_from_file(biz):
    """
    从本地文件加载BIZ专属参数（完全模拟smart_batch_auto.py）
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    
    Returns
    -------
    dict or None
        参数字典，如果不存在返回None
    """
    try:
        biz_config_file = f"params/biz_{biz}/config.py"
        
        if not os.path.exists(biz_config_file):
            logger.warning(f"⚠️  未找到BIZ专属配置: {biz_config_file}")
            return None
        
        logger.info(f"📂 加载BIZ专属配置: biz_{biz}/config.py")
        
        # 动态导入BIZ专属配置
        spec = importlib.util.spec_from_file_location("biz_config", biz_config_file)
        biz_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(biz_config)
        
        return {
            'COOKIE': biz_config.COOKIE,
            'KEY': biz_config.KEY,
            'PASS_TICKET': biz_config.PASS_TICKET,
            'UIN': biz_config.UIN,
            'BIZ': biz_config.BIZ
        }
    except Exception as e:
        logger.error(f"❌ 加载BIZ配置失败: {e}")
        return None


def fetch_articles_from_api(biz, biz_params, start_date=None, end_date=None):
    """
    从微信API获取文章列表（完全模拟smart_batch_auto.py）
    
    Parameters
    ----------
    biz : str
        公众号BIZ
    biz_params : dict
        BIZ专属参数
    start_date : datetime, optional
        开始日期
    end_date : datetime, optional
        结束日期
    
    Returns
    -------
    list or dict
        文章列表，或错误信息字典
    """
    logger.info(f"📡 从微信API获取文章列表...")
    
    # 提取appmsg_token
    appmsg_token = extract_appmsg_token_from_cookie(biz_params['COOKIE'])
    if not appmsg_token:
        logger.error("❌ 无法从Cookie提取appmsg_token")
        return {'error': 'invalid_params', 'message': '无法提取appmsg_token'}
    
    # 构造请求头
    import requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 MicroMessenger/3.4.0',
        'Cookie': biz_params['COOKIE'],
        'Referer': f'https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={biz}&scene=124',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    all_articles = []
    offset = 0
    count = 10
    has_more = True
    
    while has_more:
        api_url = (
            f"https://mp.weixin.qq.com/mp/profile_ext?"
            f"action=getmsg&"
            f"__biz={biz}&"
            f"f=json&"
            f"offset={offset}&"
            f"count={count}&"
            f"is_ok=1&"
            f"scene=124&"
            f"uin={biz_params['UIN']}&"
            f"key={biz_params['KEY']}&"
            f"pass_ticket={biz_params['PASS_TICKET']}&"
            f"wxtoken=&"
            f"appmsg_token={appmsg_token}&"
            f"x5=0"
        )
        
        try:
            logger.info(f"   获取第 {offset//count + 1} 页...")
            
            response = requests.get(api_url, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('ret') != 0:
                errmsg = data.get('errmsg', 'Unknown')
                if 'no session' in errmsg.lower():
                    logger.error(f"❌ 参数已失效: {errmsg}")
                    return {'error': 'no_session', 'message': '参数已失效，需要重新捕获'}
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
                    continue
                
                if start_date and article_date < start_date:
                    logger.info(f"   🛑 遇到早于开始日期的文章 ({article_date.date()})，停止获取")
                    has_more = False
                    break
                
                # 主文章
                article_url = app_msg_ext_info.get('content_url', '').replace('\\/', '/')
                article_title = app_msg_ext_info.get('title', '')
                
                if article_url:
                    article = {
                        'title': article_title,
                        'url': article_url,
                        'digest': app_msg_ext_info.get('digest', ''),
                        'cover': app_msg_ext_info.get('cover', ''),
                        'publish_time': publish_time,
                        'publish_date': article_date.strftime('%Y-%m-%d'),
                    }
                    all_articles.append(article)
                
                # 多图文消息
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
                            all_articles.append(sub_article)
            
            offset += count
            time.sleep(1 + (offset % 3))  # 随机延迟
            
        except Exception as e:
            logger.error(f"   ❌ 获取失败: {e}")
            break
    
    logger.info(f"✅ 从API获取 {len(all_articles)} 篇文章")
    return all_articles


def fetch_articles_smart():
    """
    智能批量获取文章（完全模拟smart_batch_auto.py + 智能增量）
    
    请求体：
    {
        "account_name": "公众号名称",
        "article_url": "任意一篇文章URL",
        "start_date": "2024-12-01",
        "end_date": "2024-12-10"
    }
    
    工作流程：
    1. 从URL提取BIZ
    2. 检查数据库已有哪些日期的文章（智能增量）
    3. 加载本地BIZ专属参数文件
    4. 检查参数有效性，失效时自动打开微信+文章重新捕获
    5. 只获取缺失日期的文章
    6. 下载HTML、获取统计数据
    7. 保存为JSON和CSV
    8. 上传到数据库
    9. 返回完整日期范围的文章（数据库已有+新获取）
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
        
        if not article_url:
            return jsonify({'success': False, 'error': '缺少必需参数: article_url'}), 400
        
        logger.info(f"📥 收到智能批量请求: 公众号={account_name}")
        
        # 1. 从URL提取BIZ
        biz = extract_biz_from_url(article_url)
        if not biz:
            return jsonify({'success': False, 'error': '无法从URL提取BIZ'}), 400
        logger.info(f"✅ 从URL提取BIZ: {biz}")
        
        # 创建或更新账号
        get_or_create_account(biz, account_name)
        
        # 2. 解析日期
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        
        # 3. 智能增量：检查数据库已有哪些日期的文章
        logger.info(f"🔍 检查数据库已有数据...")
        from database import get_db_session
        from models import Article
        
        existing_dates = set()
        missing_dates = []
        
        if start_date and end_date:
            with get_db_session() as session:
                # 获取该BIZ在日期范围内所有文章的发布日期
                existing_articles = session.query(Article.publish_date).filter(
                    Article.biz == biz,
                    Article.publish_date >= start_date.strftime('%Y-%m-%d'),
                    Article.publish_date <= end_date.strftime('%Y-%m-%d')
                ).all()
                
                for row in existing_articles:
                    if row.publish_date:
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
        
        if existing_dates:
            logger.info(f"   ✅ 数据库已有 {len(existing_dates)} 天的数据: {sorted(existing_dates)}")
        
        if not missing_dates:
            # 所有日期都有数据，直接从数据库返回
            logger.info(f"   ✅ 所有日期都有数据，直接从数据库返回")
            
            from db_operations import get_articles_by_filters
            db_articles = get_articles_by_filters(biz, start_date, end_date, None)
            
            return jsonify({
                'success': True,
                'data': {
                    'account_name': account_name,
                    'biz': biz,
                    'from_cache': True,
                    'total': len(db_articles),
                    'new_fetched': 0,
                    'articles': db_articles
                }
            })
        
        logger.info(f"   ⚠️  缺失 {len(missing_dates)} 天的数据: {missing_dates}")
        logger.info(f"   📡 需要从微信API获取缺失数据...")
        
        # 4. 加载本地BIZ专属参数
        logger.info(f"📂 加载本地BIZ专属参数...")
        biz_params = load_biz_params_from_file(biz)
        
        # 5. 检查参数有效性
        params_valid = False
        if biz_params:
            params_valid = check_params_validity(biz, biz_params)
        
        # 6. 如果参数不存在或已失效，触发自动捕获（自动打开微信+文章）
        if not biz_params or not params_valid:
            logger.warning(f"⚠️  参数{'不存在' if not biz_params else '已失效'}，开始自动捕获...")
            logger.info(f"🤖 自动打开微信并打开文章...")
            
            # 自动打开微信中的文章链接
            from wechat_automation import auto_open_article_in_wechat
            if not auto_open_article_in_wechat(article_url):
                logger.warning(f"   ⚠️  自动打开文章失败，继续尝试捕获...")
            
            # 启动代理捕获
            from api_server import ProxyManager
            if not ProxyManager.start_proxy_and_capture(article_url, biz=biz, timeout=120):
                return jsonify({
                    'success': False,
                    'error': '参数捕获失败，请确保微信已正常运行'
                }), 500
            
            time.sleep(2)
            
            # 重新加载参数
            biz_params = load_biz_params_from_file(biz)
            if not biz_params:
                return jsonify({
                    'success': False,
                    'error': '参数捕获后仍无法加载'
                }), 500
            
            # 再次检查有效性
            params_valid = check_params_validity(biz, biz_params)
            if not params_valid:
                return jsonify({
                    'success': False,
                    'error': '新捕获的参数仍然无效'
                }), 500
        
        logger.info(f"✅ 参数有效，开始获取文章")
        
        # 7. 从微信API获取文章列表（只获取缺失日期的）
        articles = fetch_articles_from_api(biz, biz_params, start_date, end_date)
        
        if isinstance(articles, dict) and articles.get('error'):
            # 如果是参数失效错误，再次尝试重新捕获
            if articles.get('error') == 'no_session':
                logger.warning(f"⚠️  获取文章时检测到参数失效，重新捕获...")
                
                # 自动打开微信中的文章
                from wechat_automation import auto_open_article_in_wechat
                auto_open_article_in_wechat(article_url)
                
                from api_server import ProxyManager
                if ProxyManager.start_proxy_and_capture(article_url, biz=biz, timeout=120):
                    time.sleep(2)
                    biz_params = load_biz_params_from_file(biz)
                    if biz_params:
                        # 重试获取文章
                        articles = fetch_articles_from_api(biz, biz_params, start_date, end_date)
                        if isinstance(articles, dict) and articles.get('error'):
                            return jsonify({
                                'success': False,
                                'error': articles.get('message', '获取文章列表失败'),
                                'need_recapture': True
                            }), 500
                    else:
                        return jsonify({
                            'success': False,
                            'error': '重新捕获后仍无法加载参数'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': '参数捕获失败'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': articles.get('message', '获取文章列表失败')
                }), 500
        
        if not articles:
            # 没有新文章，但可能数据库有旧文章
            logger.info(f"   ℹ️  没有获取到新文章")
            
            from db_operations import get_articles_by_filters
            db_articles = get_articles_by_filters(biz, start_date, end_date, None)
            
            return jsonify({
                'success': True,
                'data': {
                    'account_name': account_name,
                    'biz': biz,
                    'from_cache': True,
                    'total': len(db_articles),
                    'new_fetched': 0,
                    'articles': db_articles
                }
            })
        
        # 8. 批量下载HTML并从HTML中提取统计数据（使用参数化请求）
        logger.info(f"📊 开始批量下载HTML并提取统计数据（共 {len(articles)} 篇新文章）...")
        logger.info(f"   🔧 使用参数化请求方式（从HTML中提取统计数据）")
        
        # ✅ 关键：将BIZ参数写入new_wechat_config.py，供download_full_html使用
        _write_params_to_config(biz_params)
        
        results = []
        success_count = 0
        
        for i, article in enumerate(articles, 1):
            try:
                article_url_item = article.get('url', '')
                article_title = article.get('title', '')
                publish_date = article.get('publish_date', '')
                
                logger.info(f"   [{i}/{len(articles)}] {article_title[:40]}...")
                
                # 使用参数化请求下载HTML并提取统计数据
                # 参数已经写入params/new_wechat_config.py，download_full_html会自动读取
                download_result = download_full_html_with_stats(
                    article_url_item,
                    article_title,
                    publish_date,
                    account_name=account_name,
                    output_dir="articles_html"
                )
                
                html_file_path = download_result.get('filepath', '')
                stats = download_result.get('stats', {})
                
                if download_result.get('success') and stats:
                    success_count += 1
                    read_num = stats.get('read_num', 0)
                    old_like_count = stats.get('old_like_count', 0)
                    share_count = stats.get('share_count', 0)
                    comment_count = stats.get('comment_count', 0)
                    logger.info(f"      ✅ 阅读: {read_num} | 点赞: {old_like_count} | 分享: {share_count} | 评论: {comment_count}")
                else:
                    logger.warning(f"      ⚠️  下载或提取统计数据失败: {download_result.get('error', '')}")
                
                # 转换统计数据格式
                def safe_int(val):
                    try:
                        return int(val) if val else 0
                    except:
                        return 0
                
                # 合并数据
                result = {
                    **article,
                    'local_html_path': html_file_path,
                    'read_count': safe_int(stats.get('read_num')),
                    'like_count': safe_int(stats.get('like_count')),  # 喜欢/收藏（爱心）
                    'old_like_count': safe_int(stats.get('old_like_count')),  # 点赞（大拇指）
                    'share_count': safe_int(stats.get('share_count')),
                    'comment_count': safe_int(stats.get('comment_count')),
                    'nickname': stats.get('nickname', ''),
                    'user_name': stats.get('user_name', ''),
                    'success': download_result.get('success', False),
                    'method': 'html_extraction'
                }
                results.append(result)
                
                # 避免请求过快
                if i < len(articles):
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"      ❌ 处理失败: {e}")
                results.append({
                    **article,
                    'read_count': 0,
                    'like_count': 0,
                    'old_like_count': 0,
                    'share_count': 0,
                    'comment_count': 0,
                    'success': False,
                    'error': str(e)
                })
        
        logger.info(f"✅ 批量获取完成: 成功 {success_count}/{len(articles)}")
        
        # 9. 保存为JSON和CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"articles_{timestamp}.csv"
        json_filename = f"articles_{timestamp}.json"
        
        save_to_csv(results, csv_filename)
        save_to_json(results, json_filename)
        
        logger.info(f"💾 已保存: {csv_filename}, {json_filename}")
        
        # 10. 上传到数据库
        logger.info(f"📤 上传到数据库...")
        uploaded_count = 0
        
        for result in results:
            try:
                article_data = {
                    'biz': biz,
                    'url': result.get('url'),
                    'title': result.get('title'),
                    'html_content': None,  # HTML已保存到本地文件
                    'publish_date': result.get('publish_date'),
                    'read_count': result.get('read_count', 0),
                    'like_count': result.get('like_count', 0),
                    'old_like_count': result.get('old_like_count', 0),
                    'share_count': result.get('share_count', 0),
                    'comment_count': result.get('comment_count', 0),
                    'local_html_path': result.get('local_html_path', '')
                }
                
                save_article(article_data)
                uploaded_count += 1
                
            except Exception as e:
                logger.warning(f"   ⚠️  上传失败: {result.get('title', '')[:30]} - {e}")
        
        logger.info(f"✅ 已上传 {uploaded_count}/{len(results)} 篇新文章到数据库")
        
        # 11. 从数据库获取完整日期范围的文章（已有+新获取）
        logger.info(f"📊 从数据库获取完整日期范围的文章...")
        from db_operations import get_articles_by_filters
        all_articles = get_articles_by_filters(biz, start_date, end_date, None)
        
        logger.info(f"✅ 返回完整数据: {len(all_articles)} 篇文章（包含已有+新获取）")
        
        # 12. 返回结果
        return jsonify({
            'success': True,
            'data': {
                'account_name': account_name,
                'biz': biz,
                'from_cache': False,
                'total': len(all_articles),
                'new_fetched': uploaded_count,
                'existing_in_db': len(all_articles) - uploaded_count,
                'csv_file': csv_filename,
                'json_file': json_filename,
                'articles': all_articles  # 返回完整日期范围的所有文章
            }
        })
        
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
