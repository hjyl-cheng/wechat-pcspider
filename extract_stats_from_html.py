# -*- coding: utf-8 -*-
"""
从文章 HTML 中提取统计数据
参考原有爬虫的实现，从完整 HTML 中通过正则表达式提取阅读量、点赞数等信息
"""

import re
import time
import random
import requests
from typing import Dict, Optional


def get_article_html(url: str, headers: Dict, params: Dict = None, max_retries: int = 3) -> Optional[str]:
    """
    获取文章完整 HTML
    
    Parameters
    ----------
    url : str
        文章 URL
    headers : Dict
        请求头
    params : Dict, optional
        URL 参数
    max_retries : int
        最大重试次数
    
    Returns
    -------
    Optional[str]
        HTML 内容，失败返回 None
    """
    check_nums = 0
    while check_nums < max_retries:
        try:
            # 添加随机延时，避免请求过快
            time.sleep(random.uniform(1, 3))
            
            # 直接请求，不使用代理
            if params:
                response = requests.get(url, headers=headers, params=params, timeout=20)
            else:
                response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                return response.text
            else:
                print(f"   ⚠️  HTTP {response.status_code}")
                check_nums += 1
                
        except Exception as e:
            print(f"   ⚠️  请求失败 (尝试 {check_nums + 1}/{max_retries}): {e}")
            check_nums += 1
    
    print(f"   ❌ 多次请求失败")
    return None


def extract_stats_from_html(html: str, title: str = "") -> Dict:
    """
    从 HTML 中提取统计数据
    
    使用正则表达式从 HTML 中提取：
    - title: 标题
    - nickname: 公众号名称
    - user_name: 公众号ID
    - createTime: 创建时间
    - provinceName: 省份
    - hit_nickname: 原创标识
    - read_num: 阅读数
    - like_count: 点赞数
    - share_count: 分享数
    - comment_count: 评论数
    - article_type: 文章类型（图文/视频）
    
    Parameters
    ----------
    html : str
        文章 HTML 内容
    title : str, optional
        文章标题（备用）
    
    Returns
    -------
    Dict
        包含统计数据的字典
    """
    result = {
        'title': title,
        'nickname': '',
        'user_name': '',
        'createTime': '',
        'provinceName': '',
        'hit_nickname': '原创',
        'article_type': '图文',
        'read_num': 0,
        'like_count': 0,
        'share_count': 0,
        'comment_count': 0,
        'is_mp_video': '0',
        'success': False
    }
    
    if not html:
        return result
    
    try:
        # 提取标题
        try:
            title_match = re.findall(r"var title = '(.*?)';", html)
            if title_match:
                result['title'] = title_match[0]
        except:
            pass
        
        # 提取公众号名称
        try:
            nickname_match = re.findall(r'var nickname = htmlDecode\("(.*?)"\);', html)
            if nickname_match:
                result['nickname'] = nickname_match[0]
        except:
            pass
        
        # 提取公众号ID
        try:
            user_name_match = re.findall(r'var user_name = "(.*?)";', html)
            if user_name_match:
                result['user_name'] = user_name_match[0]
        except:
            pass
        
        # 提取发布时间
        try:
            createTime_match = re.findall(r"var createTime = '(.*?)';", html)
            if createTime_match:
                result['createTime'] = createTime_match[0]
        except:
            pass
        
        # 提取省份
        try:
            provinceName_match = re.findall(r"provinceName: '(.*?)'", html)
            if provinceName_match:
                result['provinceName'] = provinceName_match[0]
        except:
            pass
        
        # 提取原创标识
        try:
            hit_nickname_match = re.findall(r"hit_nickname: '(.*?)'", html)
            if hit_nickname_match and hit_nickname_match[0]:
                result['hit_nickname'] = hit_nickname_match[0]
            else:
                result['hit_nickname'] = '原创'
        except:
            result['hit_nickname'] = '原创'
        
        # 提取阅读数（优先使用 read_num_new）
        try:
            read_num_new_match = re.findall(r"var read_num_new = '(.*?)'", html)
            if read_num_new_match:
                result['read_num'] = int(read_num_new_match[0]) if read_num_new_match[0] else 0
            else:
                read_num_match = re.findall(r"var read_num = '(.*?)'", html)
                if read_num_match:
                    result['read_num'] = int(read_num_match[0]) if read_num_match[0] else 0
        except:
            result['read_num'] = 0
        
        # 提取点赞数（大拇指👍）
        try:
            old_like_count_match = re.findall(r"old_like_count: '(.*?)'", html)
            if old_like_count_match:
                result['old_like_count'] = int(old_like_count_match[0]) if old_like_count_match[0] else 0
        except:
            result['old_like_count'] = 0
        
        # 提取喜欢数（爱心❤️）
        try:
            like_count_match = re.findall(r"like_count: '(.*?)'", html)
            if like_count_match:
                result['like_count'] = int(like_count_match[0]) if like_count_match[0] else 0
        except:
            result['like_count'] = 0
        
        # 提取分享数
        try:
            share_count_match = re.findall(r"share_count: '(.*?)'", html)
            if share_count_match:
                result['share_count'] = int(share_count_match[0]) if share_count_match[0] else 0
        except:
            result['share_count'] = 0
        
        # 提取评论数
        try:
            comment_count_match = re.findall(r"comment_count: '(.*?)'", html)
            if comment_count_match:
                result['comment_count'] = int(comment_count_match[0]) if comment_count_match[0] else 0
        except:
            result['comment_count'] = 0
        
        # 提取视频标识
        try:
            is_mp_video_match = re.findall(r"is_mp_video: '(.*?)'", html)
            if is_mp_video_match:
                result['is_mp_video'] = is_mp_video_match[0]
        except:
            pass
        
        # 判断文章类型
        if "video_id: '" in html:
            result['article_type'] = "视频"
        else:
            result['article_type'] = "图文"
        
        result['success'] = True
        
    except Exception as e:
        print(f"   ⚠️  提取统计数据失败: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def get_article_stats_from_url(article_url: str, cookie: str = '', key: str = '', 
                                uin: str = '', pass_ticket: str = '', devicetype: str = '',
                                version: str = '', min_read_num: int = 0) -> Dict:
    """
    从文章 URL 获取完整 HTML 并提取统计数据
    
    重要：必须提供 key, uin, pass_ticket 等参数才能获取包含统计数据的完整HTML！
    这些参数需要从 PC 微信访问公众号文章时抓包获取。
    
    Parameters
    ----------
    article_url : str
        文章 URL
    cookie : str, optional
        Cookie（用于需要登录的情况）
    key : str
        从 PC 微信抓包获取的 key 参数
    uin : str
        从 PC 微信抓包获取的 uin 参数  
    pass_ticket : str
        从 PC 微信抓包获取的 pass_ticket 参数
    devicetype : str, optional
        设备类型，默认从参数配置读取
    version : str, optional
        版本号，默认从参数配置读取
    min_read_num : int, optional
        最小阅读数阈值，默认0（不过滤）
    
    Returns
    -------
    Dict
        包含统计数据的字典
    """
    print(f"   正在获取文章完整 HTML...")
    
    # 如果没有提供参数，尝试从配置文件读取
    if not key or not uin or not pass_ticket:
        try:
            from params.new_wechat_config import KEY, UIN, PASS_TICKET
            key = key or KEY
            uin = uin or UIN
            pass_ticket = pass_ticket or PASS_TICKET
            print(f"   ✅ 从配置文件读取参数")
        except:
            print(f"   ⚠️  未提供必要参数（key, uin, pass_ticket）且无法从配置读取")
            print(f"   ⚠️  将尝试直接请求（可能无法获取统计数据）")
    
    # 从 URL 中提取参数
    try:
        __biz = re.findall(r"__biz=(.*?)&", article_url)[0]
        mid = re.findall(r"mid=(.*?)&", article_url)[0]
        idx = re.findall(r"idx=(.*?)&", article_url)[0]
        sn = re.findall(r"sn=(.*?)&", article_url)
        if sn:
            sn = sn[0]
        else:
            # 如果URL末尾没有&，尝试匹配到结尾或#
            sn = re.findall(r"sn=([^&#]+)", article_url)[0]
        
        # chksm 可能不存在
        chksm_match = re.findall(r"chksm=(.*?)&", article_url)
        chksm = chksm_match[0] if chksm_match else ""
        
        # scene 可能不存在
        scene_match = re.findall(r"scene=(.*?)#", article_url)
        if not scene_match:
            scene_match = re.findall(r"scene=(.*?)&", article_url)
        scene = scene_match[0] if scene_match else "126"
        
        print(f"   ✅ 提取URL参数成功")
        print(f"      __biz: {__biz[:20]}...")
        print(f"      mid: {mid}")
        print(f"      idx: {idx}")
        print(f"      sn: {sn[:20]}...")
        
    except Exception as e:
        print(f"   ❌ 无法从URL提取参数: {e}")
        return {
            'success': False,
            'error': f'URL参数提取失败: {e}'
        }
    
    # 如果有key等参数，构造完整的请求URL和参数（参考您的代码）
    if key and uin and pass_ticket:
        # 使用带参数的请求方式（这样才能获取到统计数据）
        url = "https://mp.weixin.qq.com/s"
        
        # 如果没有提供devicetype和version，使用默认值
        if not devicetype:
            devicetype = "Windows"  # 或从配置读取
        if not version:
            version = "6309091f"  # 或从配置读取
        
        # 尝试从配置读取
        try:
            from params.new_wechat_config import COOKIE as config_cookie
            if not cookie:
                cookie = config_cookie
        except:
            pass
        
        # 从 URL 或 Cookie 中读取更多参数
        url_params = article_url.split('?')[1] if '?' in article_url else ""
        
        # 构造请求参数（参考您提供的代码）
        params = {
            "__biz": __biz,
            "mid": mid,
            "idx": idx,
            "sn": sn,
            "scene": scene,
            "key": key,
            "ascene": "1",
            "uin": uin,
            "devicetype": devicetype,
            "version": version,
            "lang": "zh_CN",
            "acctmode": "0",
            "pass_ticket": pass_ticket,
            "wx_header": "1"
        }
        
        if chksm:
            params["chksm"] = chksm
        
        print(f"   🔧 使用参数化请求方式")
        
    else:
        # 没有参数，直接请求原URL（可能获取不到统计数据）
        url = article_url
        params = None
        print(f"   ⚠️  使用直接请求方式（可能无法获取统计数据）")
    
    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    # 获取 HTML
    html = get_article_html(url, headers, params)
    
    if not html:
        return {
            'success': False,
            'error': '无法获取 HTML'
        }
    
    # 检查是否获取到了包含统计数据的HTML
    if "var read_num" not in html and "old_like_count" not in html:
        print(f"   ⚠️  HTML中未找到统计数据变量")
        print(f"   💡 提示：需要提供 key, uin, pass_ticket 参数才能获取完整HTML")
        print(f"   💡 这些参数需要从 PC 微信访问文章时抓包获取")
    
    # 提取统计数据
    stats = extract_stats_from_html(html)
    
    # 检查阅读数阈值
    if min_read_num > 0 and stats.get('read_num', 0) < min_read_num:
        print(f"   ⚠️  阅读量 {stats['read_num']} 小于阈值 {min_read_num}，跳过")
        stats['filtered'] = True
        stats['filter_reason'] = f'阅读量低于 {min_read_num}'
    else:
        stats['filtered'] = False
    
    # 检查是否是不可下载的视频
    if stats['article_type'] == "视频" and stats['is_mp_video'] == "0":
        print(f"   ⚠️  这是不可下载的视频文章")
        stats['downloadable'] = False
    else:
        stats['downloadable'] = True
    
    return stats



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
    
    print(f"\n测试提取文章统计数据...")
    print(f"URL: {test_url}")
    print()
    
    stats = get_article_stats_from_url(test_url)
    
    print("\n" + "="*80)
    print("提取结果:")
    print("="*80)
    
    if stats.get('success'):
        print(f"标题: {stats['title']}")
        print(f"公众号: {stats['nickname']} ({stats['user_name']})")
        print(f"发布时间: {stats['createTime']}")
        print(f"省份: {stats['provinceName']}")
        print(f"原创标识: {stats['hit_nickname']}")
        print(f"文章类型: {stats['article_type']}")
        print(f"阅读数: {stats['read_num']:,}")
        print(f"点赞数: {stats['like_count']:,}")
        print(f"分享数: {stats['share_count']:,}")
        print(f"评论数: {stats['comment_count']:,}")
    else:
        print(f"❌ 提取失败: {stats.get('error', 'Unknown error')}")
    
    print("="*80)
