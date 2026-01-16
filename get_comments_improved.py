# -*- coding: utf-8 -*-
"""
改进的留言获取方法
使用参数化请求来获取comment_id
"""

import re
import requests


def get_comment_id_from_html(html_content):
    """
    从HTML中提取comment_id
    支持多种格式
    """
    # 尝试多种正则模式
    patterns = [
        r'var comment_id = [\'"](\d+)[\'"]',  # var comment_id = '4288297619342147597'
        r'comment_id = "(\d+)"',  # 原始格式
        r'comment_id:\s*JsDecode\([\'"](\d+)[\'"]\)',  # JsDecode格式
        r"comment_id\.DATA['\)]\s*:\s*'(\d+)'",  # DATA格式
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content)
        if matches:
            print(f"      ✅ 使用模式匹配到 comment_id: {pattern}")
            return matches[0]
    
    return None


def get_comments_with_params(article_url, appmsg_token, cookie, key=None, uin=None, pass_ticket=None):
    """
    使用参数化请求获取留言
    
    Parameters
    ----------
    article_url : str
        文章URL
    appmsg_token : str
        appmsg_token
    cookie : str
        Cookie
    key : str, optional
        认证key
    uin : str, optional
        用户UIN
    pass_ticket : str, optional
        通行票据
        
    Returns
    -------
    dict
        留言数据
    """
    try:
        # 1. 使用参数化请求获取HTML
        print(f"      🔧 使用参数化请求获取comment_id...")
        
        # 提取URL参数
        import urllib.parse
        parsed = urllib.parse.urlparse(article_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        __biz = params.get('__biz', [''])[0]
        mid = params.get('mid', [''])[0]
        idx = params.get('idx', [''])[0]
        sn = params.get('sn', [''])[0]
        
        # 构建参数化URL
        if key and uin and pass_ticket:
            full_url = f"{article_url}&key={key}&uin={uin}&pass_ticket={urllib.parse.quote(pass_ticket)}"
        else:
            full_url = article_url
        
        # 请求HTML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': cookie
        }
        
        response = requests.get(full_url, headers=headers)
        html_content = response.text
        
        # 2. 提取comment_id
        comment_id = get_comment_id_from_html(html_content)
        
        if not comment_id:
            print(f"      ⚠️  未找到 comment_id")
            return {}
        
        print(f"      ✅ comment_id: {comment_id}")
        
        # 3. 请求留言数据（需要带上认证参数）
        import urllib.parse
        
        # 构建留言API URL，带上所有必要参数
        comment_params = {
            'action': 'getcomment',
            '__biz': __biz,
            'idx': idx,
            'comment_id': comment_id,
            'limit': '100'
        }
        
        # 添加认证参数
        if appmsg_token:
            comment_params['appmsg_token'] = appmsg_token
        if key:
            comment_params['key'] = key
        if uin:
            comment_params['uin'] = uin
        if pass_ticket:
            comment_params['pass_ticket'] = pass_ticket
        
        comment_url = "https://mp.weixin.qq.com/mp/appmsg_comment?" + urllib.parse.urlencode(comment_params)
        
        print(f"      🔧 正在获取留言列表...")
        
        # 禁用代理
        proxies = {"http": None, "https": None}
        comment_response = requests.get(comment_url, headers=headers, proxies=proxies, timeout=15)
        
        # 检查响应
        if comment_response.status_code != 200:
            print(f"      ⚠️  留言API返回状态码: {comment_response.status_code}")
            return {}
        
        # 检查响应内容
        response_text = comment_response.text
        if not response_text or response_text.strip() == '':
            print(f"      ⚠️  留言API返回空响应")
            return {}
        
        try:
            comment_data = comment_response.json()
        except Exception as json_err:
            print(f"      ⚠️  留言API返回非JSON: {response_text[:200]}")
            return {}
        
        if comment_data.get('elected_comment'):
            count = len(comment_data.get('elected_comment', []))
            total = comment_data.get('elected_comment_total_cnt', 0)
            print(f"      ✅ 成功获取 {count}/{total} 条留言")
        
        return comment_data
        
    except Exception as e:
        print(f"      ❌ 获取留言失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


if __name__ == '__main__':
    # 测试
    from params.new_wechat_config import COOKIE, KEY, UIN, PASS_TICKET
    import re
    
    match = re.search(r'appmsg_token=([^;]+)', COOKIE)
    appmsg_token = match.group(1) if match else None
    
    test_url = "https://mp.weixin.qq.com/s/-qCnTpqSuMwzBR7YYEfYtw"
    
    result = get_comments_with_params(
        test_url,
        appmsg_token,
        COOKIE,
        KEY,
        UIN,
        PASS_TICKET
    )
    
    print(f"\n结果: {result}")
