# coding: utf-8
"""
智能批量获取公众号文章信息工具
只需要一篇文章 URL，自动获取该公众号的所有文章并批量获取统计数据

功能：
1. 从单篇文章 URL 自动提取公众号 BIZ
2. 获取该公众号的所有文章列表
3. 批量下载文章 HTML 到本地
4. 批量获取文章统计数据（阅读数、点赞数、在看数、评论数）
5. 输出完整数据，包含本地 HTML 路径
"""

import re
import time
import json
import csv
import requests
from datetime import datetime, timedelta
from params.new_wechat_config import COOKIE
from wechatarticles import ArticlesInfo


def extract_appmsg_token_from_cookie(cookie):
    """从 Cookie 中提取 appmsg_token"""
    match = re.search(r'appmsg_token=([^;]+)', cookie)
    if match:
        return match.group(1)
    return None


def extract_biz_from_url(article_url):
    """从文章 URL 中提取 BIZ"""
    print(f"   原始 URL: {article_url}")
    
    # 方法1: 从完整 URL 中提取
    match = re.search(r'[?&]__biz=([^&]+)', article_url)
    if match:
        biz = match.group(1)
        print(f"   ✅ 直接提取到 BIZ: {biz}")
        return biz
    
    # 方法2: 如果是短链接，需要先访问获取完整 URL
    if 'mp.weixin.qq.com/s/' in article_url:
        print(f"   检测到短链接，正在访问获取完整 URL...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.0',
                'Cookie': COOKIE,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            # 访问短链接，获取重定向后的完整 URL
            response = requests.get(article_url, headers=headers, allow_redirects=True, timeout=15)
            final_url = response.url
            
            print(f"   重定向后的 URL: {final_url[:120]}...")
            
            # 从重定向后的 URL 中提取 BIZ
            match = re.search(r'[?&]__biz=([^&]+)', final_url)
            if match:
                biz = match.group(1)
                print(f"   ✅ 从重定向 URL 提取到 BIZ: {biz}")
                return biz
            else:
                # 尝试从响应内容中提取
                print(f"   URL 中未找到 BIZ，尝试从页面内容提取...")
                content = response.text
                match = re.search(r'var\s+biz\s*=\s*["\']([^"\']+)["\']', content)
                if not match:
                    match = re.search(r'"biz"\s*:\s*"([^"]+)"', content)
                if match:
                    biz = match.group(1)
                    print(f"   ✅ 从页面内容提取到 BIZ: {biz}")
                    return biz
                
        except Exception as e:
            print(f"   ⚠️  访问短链接失败: {e}")
            import traceback
            traceback.print_exc()
    
    return None


def get_profile_url(biz):
    """构造公众号首页 URL"""
    return f"https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={biz}&scene=124#wechat_redirect"


def download_article_html(article_url, title, publish_date, output_dir="articles_html"):
    """
    下载文章 HTML 内容
    直接使用 requests，设置合适的 headers
    下载并内联外部 CSS，使 HTML 文件可以独立显示
    
    Parameters
    ----------
    article_url : str
        文章 URL
    title : str
        文章标题（用于文件命名）
    publish_date : str
        发布日期
    output_dir : str
        输出目录
    
    Returns
    -------
    str
        HTML 文件路径，失败返回空字符串
    """
    import os
    import html as html_module
    from bs4 import BeautifulSoup
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 清理文件名（移除非法字符）
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    safe_title = safe_title[:100]  # 限制长度
    
    # 生成文件名
    filename = f"{publish_date}-{safe_title}.html"
    filepath = os.path.join(output_dir, filename)
    
    # 如果文件已存在，直接返回
    if os.path.isfile(filepath):
        return filepath
    
    try:
        # URL 解码：将 &amp; 替换为 &
        article_url = html_module.unescape(article_url)
        
        # 设置 headers（模拟浏览器）
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 禁用代理
        proxies = {"http": None, "https": None}
        
        # 下载 HTML
        response = requests.get(article_url, headers=headers, proxies=proxies, timeout=15)
        
        if response.status_code == 200:
            html_content = response.text
            
            # 检查是否是验证页面
            if "环境异常" in html_content or len(html_content) < 50000:
                print(f"      ⚠️  可能触发了验证页面（大小{len(html_content)}字节）")
                # 仍然保存，但标记可能有问题
            
            # 解析 HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有外部 CSS 链接
            css_links = soup.find_all('link', rel='stylesheet')
            
            if css_links:
                print(f"      📥 发现 {len(css_links)} 个外部CSS，正在下载...")
                
                # 收集所有CSS内容
                all_css = []
                
                for i, link in enumerate(css_links, 1):
                    css_url = link.get('href')
                    if css_url:
                        # 处理相对路径
                        if css_url.startswith('//'):
                            css_url = 'https:' + css_url
                        elif css_url.startswith('/'):
                            css_url = 'https://mp.weixin.qq.com' + css_url
                        elif not css_url.startswith('http'):
                            continue
                        
                        try:
                            # 下载 CSS
                            css_response = requests.get(css_url, headers=headers, proxies=proxies, timeout=10)
                            if css_response.status_code == 200:
                                all_css.append(f"\n/* CSS from: {css_url} */\n")
                                all_css.append(css_response.text)
                                all_css.append("\n")
                        except Exception as e:
                            print(f"      ⚠️  下载CSS失败: {css_url[:50]}... - {e}")
                
                # 如果成功下载了CSS，替换外部链接为内联样式
                if all_css:
                    # 创建一个新的 style 标签
                    style_tag = soup.new_tag('style')
                    style_tag.string = ''.join(all_css)
                    
                    # 在 head 中插入
                    if soup.head:
                        soup.head.append(style_tag)
                    
                    # 移除所有外部CSS链接
                    for link in css_links:
                        link.decompose()
                    
                    print(f"      ✅ 已内联 {len(css_links)} 个CSS文件")
            
            # 处理图片：将 data-src 替换到 src
            img_tags = soup.find_all('img')
            if img_tags:
                replaced_count = 0
                for img in img_tags:
                    data_src = img.get('data-src')
                    if data_src:
                        # 将 data-src 的值设置为 src
                        img['src'] = data_src
                        replaced_count += 1
                
                if replaced_count > 0:
                    print(f"      ✅ 已替换 {replaced_count} 个图片的 src 属性")
            
            # 更新 HTML 内容
            html_content = str(soup)
            
            # 保存 HTML
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return filepath
        else:
            print(f"      ⚠️  HTTP {response.status_code}")
            return ""
            
    except Exception as e:
        print(f"      ⚠️  下载失败: {e}")
        import traceback
        traceback.print_exc()
        return ""


def fetch_articles_from_profile(biz, start_date=None, end_date=None):
    """
    从公众号首页获取文章列表
    
    Parameters
    ----------
    biz : str
        公众号的 BIZ
    start_date : datetime, optional
        开始日期
    end_date : datetime, optional
        结束日期
    
    Returns
    -------
    list
        文章列表
    """
    
    print(f"\n{'='*80}")
    print(f"📡 正在获取公众号文章列表...")
    print(f"{'='*80}")
    print(f"BIZ: {biz}")
    if start_date and end_date:
        print(f"日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    print(f"{'='*80}\n")
    
    # 从 Cookie 中提取必要参数
    from params.new_wechat_config import UIN, KEY, PASS_TICKET
    
    # 提取 appmsg_token
    appmsg_token = extract_appmsg_token_from_cookie(COOKIE)
    if not appmsg_token:
        print("⚠️  警告：未找到 appmsg_token")
        appmsg_token = ""
    
    # 构造请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 MicroMessenger/3.4.0',
        'Cookie': COOKIE,
        'Referer': f'https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={biz}&scene=124',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    # ✅ 创建 ArticlesInfo 实例（用于获取留言数据）
    try:
        from wechatarticles import ArticlesInfo
        articles_info = ArticlesInfo(appmsg_token, COOKIE)
        print("✅ ArticlesInfo 实例已创建（支持留言注入）")
    except Exception as e:
        print(f"⚠️  ArticlesInfo 创建失败: {e}")
        print("   留言注入功能将不可用")
        articles_info = None
    
    all_articles = []
    offset = 0
    count = 10  # 每次获取10篇
    
    while True:
        # 构造 API URL - 使用真实参数
        api_url = (
            f"https://mp.weixin.qq.com/mp/profile_ext?"
            f"action=getmsg&"
            f"__biz={biz}&"
            f"f=json&"
            f"offset={offset}&"
            f"count={count}&"
            f"is_ok=1&"
            f"scene=124&"
            f"uin={UIN}&"
            f"key={KEY}&"
            f"pass_ticket={PASS_TICKET}&"
            f"wxtoken=&"
            f"appmsg_token={appmsg_token}&"
            f"x5=0"
        )
        
        try:
            print(f"   正在获取第 {offset//count + 1} 页...")
            
            response = requests.get(api_url, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('ret') != 0:
                print(f"   ⚠️  API 返回错误: {data.get('errmsg', 'Unknown error')}")
                print(f"   返回数据: {json.dumps(data, ensure_ascii=False)[:200]}")
                break
            
            # 解析文章列表
            general_msg_list = data.get('general_msg_list', {})
            if isinstance(general_msg_list, str):
                general_msg_list = json.loads(general_msg_list)
            
            msg_list = general_msg_list.get('list', [])
            
            if not msg_list:
                print(f"   ✅ 已获取所有文章")
                break
            
            # 处理每条消息
            for msg in msg_list:
                comm_msg_info = msg.get('comm_msg_info', {})
                app_msg_ext_info = msg.get('app_msg_ext_info', {})
                
                if not app_msg_ext_info:
                    continue
                
                # 获取发布时间
                publish_time = comm_msg_info.get('datetime', 0)
                
                # 检查日期范围
                if start_date and end_date:
                    article_date = datetime.fromtimestamp(publish_time)
                    if article_date < start_date or article_date > end_date + timedelta(days=1):
                        continue
                
                # 主文章
                article_url = app_msg_ext_info.get('content_url', '').replace('\\/', '/')
                article_title = app_msg_ext_info.get('title', '')
                article_date = datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d')
                
                # 下载文章 HTML（包含统计数据的完整版本 + 留言）
                print(f"      正在下载完整 HTML: {article_title[:30]}...")
                from download_full_html import download_full_html_with_stats
                full_result = download_full_html_with_stats(
                    article_url, 
                    article_title, 
                    article_date, 
                    output_dir="articles_html",
                    inject_comments=True,  # ✅ 启用留言注入
                    articles_info=articles_info  # ✅ 传入ArticlesInfo实例
                )
                html_file = full_result.get('filepath', '')
                
                # ✅ 直接使用下载时提取的统计数据，避免重复请求
                extracted_stats = full_result.get('stats', {})
                
                time.sleep(0.5)  # 避免请求过快
                
                article = {
                    'title': article_title,
                    'url': article_url,
                    'local_html_path': html_file,
                    'digest': app_msg_ext_info.get('digest', ''),
                    'cover': app_msg_ext_info.get('cover', ''),
                    'publish_time': publish_time,
                    'publish_date': datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d'),
                    # ✅ 保存下载时提取的统计数据
                    '_extracted_stats': extracted_stats,
                }
                
                if article['url']:
                    all_articles.append(article)
                
                # 多图文消息
                multi_app_msg_item_list = app_msg_ext_info.get('multi_app_msg_item_list', [])
                for item in multi_app_msg_item_list:
                    sub_article_url = item.get('content_url', '').replace('\\/', '/')
                    sub_article_title = item.get('title', '')
                    sub_article_date = datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d')
                    
                    print(f"      正在下载完整 HTML: {sub_article_title[:30]}...")
                    sub_full_result = download_full_html_with_stats(sub_article_url, sub_article_title, sub_article_date, output_dir="articles_html")
                    sub_html_file = sub_full_result.get('filepath', '')
                    time.sleep(0.5)  # 避免请求过快
                    
                    sub_article = {
                        'title': sub_article_title,
                        'url': sub_article_url,
                        'local_html_path': sub_html_file,
                        'digest': item.get('digest', ''),
                        'cover': item.get('cover', ''),
                        'publish_time': publish_time,
                        'publish_date': datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d'),
                    }
                    
                    if sub_article['url']:
                        all_articles.append(sub_article)
            
            print(f"   已获取 {len(all_articles)} 篇文章")
            
            # 只获取第一页，不继续循环
            print(f"   ✅ 已获取第一页文章（如需更多，可修改代码）")
            break
            
        except Exception as e:
            print(f"   ❌ 获取失败: {e}")
            break
    
    print(f"\n{'='*80}")
    print(f"✅ 文章列表获取完成")
    print(f"{'='*80}")
    print(f"总共获取: {len(all_articles)} 篇文章")
    print(f"{'='*80}\n")
    
    return all_articles


def get_article_stats(article_url, articles_info=None, use_html_extraction=True):
    """
    获取单篇文章的统计数据
    
    Parameters
    ----------
    article_url : str
        文章 URL
    articles_info : ArticlesInfo, optional
        ArticlesInfo 实例（用于 API 方式）
    use_html_extraction : bool
        是否使用 HTML 提取方式（推荐，更稳定）
    
    Returns
    -------
    dict
        统计数据
    """
    # 优先使用 HTML 提取方式
    if use_html_extraction:
        try:
            from extract_stats_from_html import get_article_stats_from_url
            from params.new_wechat_config import KEY, UIN, PASS_TICKET
            
            # 从 HTML 提取统计数据（传入必要的参数以获取完整HTML）
            stats = get_article_stats_from_url(
                article_url, 
                cookie=COOKIE,
                key=KEY,
                uin=UIN,
                pass_ticket=PASS_TICKET
            )
            
            if stats.get('success'):
                return {
                    'read_count': stats.get('read_num', 0),
                    'old_like_count': stats.get('old_like_count', 0),  # 点赞（大拇指👍）
                    'like_count': stats.get('like_count', 0),  # 喜欢/收藏（爱心❤️）
                    'comment_count': stats.get('comment_count', 0),
                    'share_count': stats.get('share_count', 0),
                    'nickname': stats.get('nickname', ''),
                    'user_name': stats.get('user_name', ''),
                    'createTime': stats.get('createTime', ''),
                    'article_type': stats.get('article_type', '图文'),
                    'success': True,
                    'method': 'html_extraction'
                }
            else:
                # HTML 提取失败，尝试 API 方式
                print(f"      ⚠️  HTML 提取失败，尝试 API 方式...")
                if articles_info:
                    return get_article_stats_api(article_url, articles_info)
                else:
                    return {
                        'read_count': 'N/A',
                        'like_count': 'N/A',
                        'comment_count': 'N/A',
                        'share_count': 'N/A',
                        'success': False,
                        'error': 'HTML extraction failed and no API instance provided'
                    }
        except Exception as e:
            print(f"      ⚠️  HTML 提取出错: {e}")
            # 如果有 API 实例，尝试使用 API 方式
            if articles_info:
                print(f"      尝试使用 API 方式...")
                return get_article_stats_api(article_url, articles_info)
            else:
                return {
                    'read_count': 'N/A',
                    'like_count': 'N/A',
                    'comment_count': 'N/A',
                    'share_count': 'N/A',
                    'success': False,
                    'error': str(e)
                }
    else:
        # 使用 API 方式
        if articles_info:
            return get_article_stats_api(article_url, articles_info)
        else:
            return {
                'read_count': 'N/A',
                'like_count': 'N/A',
                'comment_count': 'N/A',
                'share_count': 'N/A',
                'success': False,
                'error': 'No API instance provided'
            }


def get_article_stats_api(article_url, articles_info):
    """
    使用 API 方式获取文章统计数据（备用方式）
    
    Parameters
    ----------
    article_url : str
        文章 URL
    articles_info : ArticlesInfo
        ArticlesInfo 实例
    
    Returns
    -------
    dict
        统计数据
    """
    try:
        # 获取阅读数和点赞数
        read_num, like_num, old_like_num = articles_info.read_like_nums(article_url)
        
        # 获取评论数
        comments_data = articles_info.comments(article_url)
        comment_count = comments_data.get('elected_comment_total_cnt', 0) if comments_data else 0
        
        return {
            'read_count': read_num,
            'like_count': like_num,
            'old_like_count': old_like_num,
            'comment_count': comment_count,
            'share_count': 0,  # API 方式无法获取分享数
            'success': True,
            'method': 'api'
        }
    except Exception as e:
        return {
            'read_count': 'N/A',
            'like_count': 'N/A',
            'old_like_count': 'N/A',
            'comment_count': 'N/A',
            'share_count': 'N/A',
            'success': False,
            'error': str(e),
            'method': 'api'
        }


def parse_date_range(date_str):
    """解析日期范围"""
    if not date_str:
        return None, None
    
    # 尝试不同的分隔符
    for sep in [' 到 ', '~', ',']:
        if sep in date_str:
            parts = date_str.split(sep)
            if len(parts) == 2:
                try:
                    start_date = datetime.strptime(parts[0].strip(), '%Y-%m-%d')
                    end_date = datetime.strptime(parts[1].strip(), '%Y-%m-%d')
                    return start_date, end_date
                except:
                    continue
    
    # 单个日期
    try:
        date = datetime.strptime(date_str.strip(), '%Y-%m-%d')
        return date, date
    except:
        return None, None


def save_to_csv(data, filename):
    """保存数据到 CSV"""
    if not data:
        return
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = [
            'title', 'url', 'local_html_path', 'publish_date',
            'nickname', 'user_name', 'article_type',
            'read_count', 'old_like_count', 'share_count', 'like_count', 'comment_count',
            'digest'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV 已保存: {filename}")




def save_to_json(data, filename):
    """保存数据到 JSON"""
    if not data:
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON 已保存: {filename}")


def main():
    """主函数"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          智能批量获取公众号文章信息工具                   ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # 输入文章 URL
    print("📝 请输入公众号的任意一篇文章 URL:\n")
    article_url = input("文章 URL: ").strip()
    
    if not article_url:
        print("❌ URL 不能为空")
        return
    
    # 提取 BIZ
    print(f"\n🔍 正在提取 BIZ...")
    biz = extract_biz_from_url(article_url)
    
    if not biz:
        print("❌ 无法从 URL 中提取 BIZ")
        print("💡 请确保 URL 格式正确，例如:")
        print("   https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx...")
        return
    
    print(f"✅ BIZ: {biz}")
    
    # 输入日期范围（可选）
    print(f"\n📅 请输入日期范围（可选，直接回车获取所有文章）:")
    print(f"   格式: 2024-12-01 到 2024-12-10\n")
    
    date_range_str = input("日期范围: ").strip()
    start_date, end_date = parse_date_range(date_range_str)
    
    if date_range_str and (not start_date or not end_date):
        print("❌ 日期格式错误")
        return
    
    # 获取文章列表
    articles = fetch_articles_from_profile(biz, start_date, end_date)
    
    if not articles:
        print("\n⚠️  没有获取到文章")
        return
    
    # 提取 appmsg_token
    appmsg_token = extract_appmsg_token_from_cookie(COOKIE)
    if not appmsg_token:
        print("❌ 无法从 Cookie 中提取 appmsg_token")
        return
    
    # 创建 ArticlesInfo 实例
    articles_info = ArticlesInfo(appmsg_token, COOKIE)
    
    # 批量获取统计数据
    print(f"📊 开始批量获取统计数据...\n")
    
    results = []
    success_count = 0
    
    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {article['title']}")
        print(f"   发布时间: {article['publish_date']}")
        
        # ✅ 优先使用下载时已提取的统计数据（避免重复请求）
        
        if article.get('_extracted_stats') and isinstance(article.get('_extracted_stats'), dict) and len(article['_extracted_stats']) > 0:
            print(f"   ✅ 使用下载时提取的统计数据（无需重复请求）")
            extracted = article['_extracted_stats']
            stats = {
                'read_count': int(extracted.get('read_num', 0)) if extracted.get('read_num') else 0,
                'old_like_count': int(extracted.get('old_like_count', 0)) if extracted.get('old_like_count') else 0,  # 点赞（大拇指👍）
                'like_count': int(extracted.get('like_count', 0)) if extracted.get('like_count') else 0,  # 喜欢/收藏（爱心❤️）
                'comment_count': int(extracted.get('comment_count', 0)) if extracted.get('comment_count') else 0,
                'share_count': int(extracted.get('share_count', 0)) if extracted.get('share_count') else 0,
                'nickname': extracted.get('nickname', ''),
                'user_name': extracted.get('user_name', ''),
                'article_type': extracted.get('article_type', '图文'),
                'success': True,
                'method': 'from_download_cache'
            }
        else:
            # 如果下载时没有提取到，再请求一次
            print(f"   正在获取统计数据...")
            stats = get_article_stats(article['url'], articles_info)
        
        if stats['success']:
            success_count += 1
            share_info = f" | 分享: {stats['share_count']}" if stats.get('share_count', 0) > 0 else ""
            method_info = f" [{stats.get('method', 'unknown')}]" if 'method' in stats else ""
            # ✅ 输出顺序：阅读量、点赞、分享、喜欢、评论
            print(f"   ✅ 阅读: {stats['read_count']:,} | 点赞: {stats.get('old_like_count', 0):,} | 分享: {stats['share_count']:,} | 喜欢: {stats.get('like_count', 0):,} | 评论: {stats['comment_count']}{method_info}")
        else:
            print(f"   ❌ 获取失败{': ' + stats.get('error', '') if stats.get('error') else ''}")
        
        # 合并数据
        result = {**article, **stats}
        results.append(result)
        
        # 避免请求过快
        if i < len(articles):
            time.sleep(2)
        
        print()
    
    print(f"{'='*80}")
    print(f"✅ 批量获取完成")
    print(f"{'='*80}")
    print(f"总共: {len(articles)} 篇文章")
    print(f"成功: {success_count} 篇")
    print(f"失败: {len(articles) - success_count} 篇")
    print(f"{'='*80}\n")
    
    # 保存数据
    print("💾 保存数据...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    csv_filename = f"articles_{timestamp}.csv"
    json_filename = f"articles_{timestamp}.json"
    
    save_to_csv(results, csv_filename)
    save_to_json(results, json_filename)
    
    print(f"\n🎉 完成！共获取 {len(results)} 篇文章的数据")


if __name__ == "__main__":
    main()
