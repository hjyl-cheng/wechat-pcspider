# -*- coding: utf-8 -*-
"""
改进的留言区注入方案 - 参考 wechat-article-exporter
直接渲染DOM元素，无需拦截请求
"""

import re
import json
from bs4 import BeautifulSoup


def inject_comments_direct_render(html_file, comments_data):
    """
    直接在HTML中渲染留言区DOM元素
    不依赖Ajax拦截，100%可靠
    
    Parameters
    ----------
    html_file : str
        HTML文件路径
    comments_data : dict
        评论数据
        
    Returns
    -------
    bool
        是否成功
    """
    if not comments_data:
        print("      ⚠️  没有留言数据")
        return False
    
    try:
        # 读取HTML
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找head和body标签
        head = soup.find('head')
        body = soup.find('body')
        
        if not head or not body:
            print("      ❌ 未找到head或body标签")
            return False
        
        # 1. 先在head中注入CSS样式
        style_tag = soup.new_tag('style')
        style_tag.string = get_comments_css()
        head.append(style_tag)
        
        # 2. 生成留言区HTML
        comments_html = generate_wechat_style_comments(comments_data)
        
        # 3. 在body结束前插入
        comments_section = BeautifulSoup(comments_html, 'html.parser')
        body.append(comments_section)
        
        # 保存
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        comment_count = len(comments_data.get('elected_comment', []))
        total_count = comments_data.get('elected_comment_total_cnt', 0)
        
        print(f"      ✅ 已渲染 {comment_count}/{total_count} 条留言到HTML")
        return True
        
    except Exception as e:
        print(f"      ❌ 留言渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_comments_css():
    """
    获取留言区CSS样式
    """
    return """
/* 留言区样式 - 100%还原微信样式 */
#js_cmt_area {
    padding: 20px;
    background: #fafafa;
    margin-top: 30px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.discuss_title {
    font-size: 18px;
    font-weight: 600;
    color: #333;
    margin: 0 0 15px 0;
    padding: 0;
}

.cmt_write_wrp {
    margin: 15px 0;
    padding: 10px;
    background: white;
    border-radius: 4px;
}

.cmt_write_input {
    color: #999;
    padding: 8px;
}

.discuss_list {
    background: white;
    border-radius: 4px;
}

.discuss_item {
    padding: 15px;
    border-bottom: 1px solid #eee;
}

.discuss_item:last-child {
    border-bottom: none;
}

.discuss_opr {
    display: flex;
    align-items: flex-start;
}

.discuss_avatar_wrp {
    flex-shrink: 0;
    margin-right: 10px;
}

.discuss_avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
}

.discuss_main {
    flex: 1;
    min-width: 0;
}

.discuss_author {
    display: flex;
    align-items: center;
    margin-bottom: 5px;
}

.discuss_author_name {
    font-size: 14px;
    color: #576b95;
    font-weight: 500;
    margin-right: 8px;
}

.discuss_info {
    font-size: 12px;
    color: #999;
}

.discuss_message {
    font-size: 15px;
    line-height: 1.6;
    color: #333;
    word-wrap: break-word;
    margin: 8px 0;
}

.discuss_extra_info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 8px;
}

.discuss_author_reply_tag {
    display: inline-block;
    padding: 2px 8px;
    background: #f5f5f5;
    border-radius: 3px;
    font-size: 12px;
    color: #888;
}

.discuss_like_wrp {
    display: flex;
    align-items: center;
    font-size: 13px;
    color: #999;
}

.discuss_like_icon {
    margin-right: 4px;
}

.discuss_liked {
    color: #fa5151;
}

/* 作者回复 */
.author_reply_wrp {
    margin-top: 10px;
    padding: 10px;
    background: #f7f7f7;
    border-radius: 4px;
    border-left: 3px solid #576b95;
}

.author_reply_author {
    font-size: 13px;
    color: #576b95;
    font-weight: 500;
    margin-bottom: 5px;
}

.author_reply_content {
    font-size: 14px;
    color: #333;
    line-height: 1.5;
}

.author_reply_time {
    font-size: 12px;
    color: #999;
    margin-top: 5px;
}

/* 二级留言 */
.reply_list_wrp {
    margin-top: 12px;
    padding: 12px;
    background: #f9f9f9;
    border-radius: 4px;
}

.reply_item {
    padding: 8px 0;
    border-bottom: 1px solid #eee;
}

.reply_item:last-child {
    border-bottom: none;
}

.reply_author {
    font-size: 13px;
    color: #576b95;
    font-weight: 500;
}

.reply_content {
    font-size: 14px;
    color: #333;
    margin-top: 4px;
    line-height: 1.5;
}

.reply_info {
    font-size: 12px;
    color: #999;
    margin-top: 4px;
}
"""


def generate_wechat_style_comments(comments_data):
    """
    生成微信风格的留言区HTML（不含CSS）
    """
    elected_comments = comments_data.get('elected_comment', [])
    if not elected_comments:
        return ""
    
    total_count = comments_data.get('elected_comment_total_cnt', len(elected_comments))
    
    # 开始构建HTML
    html = f'''
<div id="js_cmt_area">
    <h3 class="discuss_title">留言 {total_count}</h3>
    
    <div class="cmt_write_wrp">
        <div class="cmt_write_input">✏️ 写留言</div>
    </div>
    
    <div id="cmt_list" class="discuss_list">
'''
    
    # 渲染每条留言
    for comment in elected_comments:
        comment_html = generate_single_comment_dom(comment)
        html += comment_html
    
    html += '''
    </div>
</div>
'''
    
    return html


def generate_single_comment_dom(comment):
    """
    生成单条留言的DOM元素
    """
    import time
    
    nick_name = comment.get('nick_name', '匿名')
    logo_url = comment.get('logo_url', 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22%3E%3Ccircle cx=%2220%22 cy=%2220%22 r=%2220%22 fill=%22%23ddd%22/%3E%3C/svg%3E')
    content = comment.get('content', '')
    create_time = comment.get('create_time', 0)
    like_num = comment.get('like_num', 0)
    
    # 格式化时间
    try:
        time_str = time.strftime('%m月%d日', time.localtime(create_time))
    except:
        time_str = '最近'
    
    # 是否被作者赞过
    is_author_liked = comment.get('is_elected', 0) == 1
    
    html = f'''
    <div class="discuss_item">
        <div class="discuss_opr">
            <div class="discuss_avatar_wrp">
                <img class="discuss_avatar" src="{logo_url}" alt="{nick_name}">
            </div>
            <div class="discuss_main">
                <div class="discuss_author">
                    <span class="discuss_author_name">{nick_name}</span>
                    <span class="discuss_info">{time_str}</span>
                </div>
                <div class="discuss_message">{content}</div>
                <div class="discuss_extra_info">
                    <div>
'''
    
    # 作者赞过标签
    if is_author_liked:
        html += '                        <span class="discuss_author_reply_tag">作者赞过</span>\n'
    
    html += '                    </div>\n'
    
    # 点赞数
    if like_num > 0:
        html += f'''
                    <div class="discuss_like_wrp">
                        <span class="discuss_like_icon">❤️</span>
                        <span class="discuss_like_num">{like_num}</span>
                    </div>
'''
    
    html += '                </div>\n'
    
    # 作者回复和二级留言（使用reply_new字段）
    reply_new = comment.get('reply_new', {})
    
    # 作者回复
    if reply_new and reply_new.get('reply_list'):
        reply_list = reply_new.get('reply_list', [])
        
        # 遍历所有回复
        for sub_reply in reply_list:
            # 判断是否是作者回复
            is_author = sub_reply.get('is_from_publisher', 0) == 1 or sub_reply.get('type', 0) == 1
            
            sub_content = sub_reply.get('content', '')
            sub_nick = sub_reply.get('nick_name', '作者')
            sub_time = sub_reply.get('create_time', 0)
            
            try:
                sub_time_str = time.strftime('%m月%d日', time.localtime(sub_time))
            except:
                sub_time_str = '最近'
            
            if is_author:
                # 作者回复 - 特殊样式
                html += f'''
                <div class="author_reply_wrp">
                    <div class="author_reply_author">📝 {sub_nick} 作者</div>
                    <div class="author_reply_content">{sub_content}</div>
                    <div class="author_reply_time">{sub_time_str}</div>
                </div>
'''
    
    # 二级留言（普通用户回复）
    if reply_new and reply_new.get('reply_list'):
        reply_list = reply_new.get('reply_list', [])
        
        # 过滤出非作者回复
        user_replies = [r for r in reply_list if r.get('is_from_publisher', 0) != 1 and r.get('type', 0) != 1]
        
        if user_replies:
            html += '                <div class="reply_list_wrp">\n'
            for sub_reply in user_replies:
                sub_content = sub_reply.get('content', '')
                sub_nick = sub_reply.get('nick_name', '匿名')
                sub_time = sub_reply.get('create_time', 0)
                try:
                    sub_time_str = time.strftime('%m月%d日', time.localtime(sub_time))
                except:
                    sub_time_str = '最近'
                
                html += f'''
                    <div class="reply_item">
                        <div class="reply_author">{sub_nick}</div>
                        <div class="reply_content">{sub_content}</div>
                        <div class="reply_info">{sub_time_str}</div>
                    </div>
'''
            html += '                </div>\n'
    
    html += '''
            </div>
        </div>
    </div>
'''
    
    return html


if __name__ == '__main__':
    # 测试
    test_comments = {
        'elected_comment_total_cnt': 70,
        'elected_comment': [
            {
                'nick_name': '爱美4144 M',
                'logo_url': '',
                'content': '勤其治家',
                'create_time': 1734062400,
                'like_num': 7,
                'is_elected': 1,
                'reply': {}
            },
            {
                'nick_name': 'Sunrise',
                'logo_url': '',
                'content': '会赚钱不如会规划',
                'create_time': 1734062600,
                'like_num': 6,
                'reply': {
                    'content': '对呀',
                    'create_time': 1734062700
                }
            }
        ]
    }
    
    html = generate_wechat_style_comments(test_comments)
    print(html)
