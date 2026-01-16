# -*- coding: utf-8 -*-
"""
下载包含统计数据的完整HTML（含评论区数据）
"""

import re
import os
import requests
from bs4 import BeautifulSoup


def download_full_html_with_stats(article_url, title, publish_date, 
                                   account_name=None,
                                   output_dir="articles_html",
                                   inject_comments=False,
                                   articles_info=None):
    """
    下载包含统计数据的完整HTML
    
    使用参数化请求获取包含统计数据的HTML，并保存到文件
    
    Parameters
    ----------
    article_url : str
        文章 URL
    title : str
        文章标题（用于文件命名）
    publish_date : str
        发布日期（格式：YYYY-MM-DD）
    account_name : str, optional
        公众号名称（用于创建子目录）
    output_dir : str
        输出根目录
    inject_comments : bool
        是否注入评论到HTML（默认False）
    articles_info : ArticlesInfo
        ArticlesInfo实例，用于获取评论数据（inject_comments=True时需要）
    
    Returns
    -------
    dict
        包含文件路径和提取的统计数据
    """
    # 构建目录结构：articles_html/{公众号名称}/{日期}/
    if account_name:
        # 清理公众号名称（移除非法字符）
        safe_account_name = re.sub(r'[\u003c\u003e:\"/\\\\|?*]', '_', account_name)
        safe_account_name = safe_account_name[:50]  # 限制长度
        
        # 提取日期（YYYY-MM-DD）
        if publish_date:
            date_str = publish_date  # 已经是 YYYY-MM-DD 格式
        else:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        # 创建目录：articles_html/{公众号}/{日期}/
        account_dir = os.path.join(output_dir, safe_account_name)
        date_dir = os.path.join(account_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)
        
        final_output_dir = date_dir
    else:
        # 如果没有公众号名称，使用原来的逻辑
        os.makedirs(output_dir, exist_ok=True)
        final_output_dir = output_dir
    
    # 清理文件名（移除非法字符）
    safe_title = re.sub(r'[\u003c\u003e:\"/\\\\|?*]', '_', title)
    safe_title = safe_title[:100]  # 限制长度
    
    # 生成文件名
    filename = f"{safe_title}.html"
    filepath = os.path.join(final_output_dir, filename)
    
    # 如果文件已存在，直接返回
    if os.path.isfile(filepath):
        print(f"      ✅ 完整HTML已存在: {filepath}")
        return {'filepath': filepath, 'exists': True}
    
    try:
        # 导入参数
        from params.new_wechat_config import KEY, UIN, PASS_TICKET, COOKIE
        
        # URL 解码
        import html as html_module
        article_url = html_module.unescape(article_url)
        
        # 从URL提取参数
        __biz = re.findall(r"__biz=(.*?)&", article_url)[0]
        mid = re.findall(r"mid=(.*?)&", article_url)[0]
        idx = re.findall(r"idx=(.*?)&", article_url)[0]
        sn = re.findall(r"sn=([^&#]+)", article_url)[0]
        
        # 可选参数
        chksm_match = re.findall(r"chksm=(.*?)&", article_url)
        chksm = chksm_match[0] if chksm_match else ""
        
        scene_match = re.findall(r"scene=(.*?)#", article_url)
        if not scene_match:
            scene_match = re.findall(r"scene=(.*?)&", article_url)
        scene = scene_match[0] if scene_match else "126"
        
        # 构造参数化请求
        url = "https://mp.weixin.qq.com/s"
        params = {
            "__biz": __biz,
            "mid": mid,
            "idx": idx,
            "sn": sn,
            "scene": scene,
            "key": KEY,
            "uin": UIN,
            "pass_ticket": PASS_TICKET,
            "devicetype": "Windows",
            "version": "6309091f",
            "lang": "zh_CN",
            "acctmode": "0",
            "ascene": "1",
            "wx_header": "1"
        }
        
        if chksm:
            params["chksm"] = chksm
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cookie': COOKIE
        }
        
        # 禁用代理
        proxies = {"http": None, "https": None}
        
        print(f"      🔧 正在下载包含统计数据的完整HTML...")
        
        # 下载 HTML
        response = requests.get(url, params=params, headers=headers, proxies=proxies, timeout=15)
        
        if response.status_code == 200:
            html_content = response.text
            
            # 检查是否包含统计数据
            has_read_num = "var read_num" in html_content
            has_like_count = "old_like_count" in html_content
            has_share_count = "share_count" in html_content
            has_comment_count = "comment_count" in html_content
            
            print(f"      📊 统计数据检查:")
            print(f"         - 阅读数变量: {'✅' if has_read_num else '❌'}")
            print(f"         - 点赞数变量: {'✅' if has_like_count else '❌'}")
            print(f"         - 分享数变量: {'✅' if has_share_count else '❌'}")
            print(f"         - 评论数变量: {'✅' if has_comment_count else '❌'}")
            
            # 提取统计数据值（用于返回给调用者）
            stats = {}
            try:
                read_match = re.findall(r"var read_num = '(.*?)'", html_content)
                if not read_match:
                    read_match = re.findall(r"var read_num_new = '(.*?)'", html_content)
                if read_match:
                    stats['read_num'] = read_match[0]
                    # 不打印阅读数（避免重复）
            except:
                pass
            
            try:
                # 点赞（大拇指👍）
                old_like_match = re.findall(r"old_like_count: '(.*?)'", html_content)
                if old_like_match:
                    stats['old_like_count'] = old_like_match[0]
                    print(f"      ✅ 点赞数: {stats['old_like_count']}")
            except:
                pass
            
            try:
                # 喜欢（爱心❤️）
                like_match = re.findall(r"like_count: '(.*?)'", html_content)
                if like_match:
                    stats['like_count'] = like_match[0]
                    # 不打印喜欢数（避免混淆）
            except:
                pass
            
            try:
                share_match = re.findall(r"share_count: '(.*?)'", html_content)
                if share_match:
                    stats['share_count'] = share_match[0]
                    print(f"      ✅ 分享数: {stats['share_count']}")
            except:
                pass
            
            try:
                comment_match = re.findall(r"comment_count: '(.*?)'", html_content)
                if comment_match:
                    stats['comment_count'] = comment_match[0]
                    print(f"      ✅ 评论数: {stats['comment_count']}")
            except:
                pass
            
            # 解析HTML并内联CSS
            print(f"      📥 正在处理HTML...")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有外部 CSS 链接
            css_links = soup.find_all('link', rel='stylesheet')
            
            if css_links:
                print(f"      📥 发现 {len(css_links)} 个外部CSS，正在下载...")
                
                # 收集所有CSS内容
                all_css = []
                
                for link in css_links:
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
                            css_response = requests.get(css_url, headers=headers, proxies=proxies, timeout=10)
                            if css_response.status_code == 200:
                                all_css.append(f"\n/* CSS from: {css_url} */\n")
                                all_css.append(css_response.text)
                                all_css.append("\n")
                        except:
                            pass
                
                # 内联CSS
                if all_css:
                    style_tag = soup.new_tag('style')
                    style_tag.string = ''.join(all_css)
                    
                    if soup.head:
                        soup.head.append(style_tag)
                    
                    for link in css_links:
                        link.decompose()
                    
                    print(f"      ✅ 已内联 {len(css_links)} 个CSS文件")
            
            # 处理图片
            img_tags = soup.find_all('img')
            if img_tags:
                replaced_count = 0
                for img in img_tags:
                    data_src = img.get('data-src')
                    if data_src:
                        img['src'] = data_src
                        replaced_count += 1
                
                if replaced_count > 0:
                    print(f"      ✅ 已替换 {replaced_count} 个图片的 src 属性")
            
            # 保存HTML
            html_content = str(soup)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            file_size = os.path.getsize(filepath)
            print(f"      ✅ 完整HTML已保存: {filepath}")
            print(f"      📦 文件大小: {file_size:,} 字节 ({file_size/1024/1024:.2f} MB)")
            
            # ✅ 注入留言（如果需要）
            if inject_comments and articles_info:
                print(f"      💬 正在获取并注入留言...")
                try:
                    # 使用改进的方法获取留言
                    from get_comments_improved import get_comments_with_params
                    from params.new_wechat_config import KEY, UIN, PASS_TICKET
                    
                    comments_data = get_comments_with_params(
                        article_url,
                        articles_info.appmsg_token,
                        articles_info.headers['Cookie'],
                        KEY,
                        UIN,
                        PASS_TICKET
                    )
                    
                    if comments_data and comments_data.get('elected_comment'):
                        from inject_comments_dom import inject_comments_direct_render
                        comment_count = comments_data.get('elected_comment_total_cnt', 0)
                        comment_list_len = len(comments_data.get('elected_comment', []))
                        print(f"      ✅ 准备渲染 {comment_list_len}/{comment_count} 条留言")
                        inject_comments_direct_render(filepath, comments_data)
                    else:
                        print(f"      ⚠️  未能获取到留言数据")
                except Exception as e:
                    print(f"      ⚠️  留言注入失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            return {
                'filepath': filepath,
                'exists': False,
                'stats': stats,
                'file_size': file_size,
                'success': True
            }
        else:
            print(f"      ❌ HTTP {response.status_code}")
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        print(f"      ❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


if __name__ == '__main__':
    # 测试代码
    import sys
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = input("请输入文章URL: ").strip()
    
    if not test_url:
        print("URL 不能为空")
        sys.exit(1)
    
    print(f"\n测试下载包含统计数据的完整HTML...")
    print(f"URL: {test_url}")
    print()
    
    result = download_full_html_with_stats(
        test_url,
        "测试文章",
        "2025-12-13"
    )
    
    print("\n" + "="*80)
    print("下载结果:")
    print("="*80)
    
    if result.get('success'):
        print(f"✅ 成功!")
        print(f"文件路径: {result['filepath']}")
        if result.get('stats'):
            print(f"\n提取的统计数据:")
            for key, value in result['stats'].items():
                print(f"  {key}: {value}")
    else:
        print(f"❌ 失败: {result.get('error')}")
    
    print("="*80)
