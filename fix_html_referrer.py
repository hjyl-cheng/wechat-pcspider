# coding: utf-8
"""
修复现有HTML文件的图片防盗链问题
添加 Referrer Policy meta 标签
"""
import os
import re
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_html_referrer(html_file):
    """
    给HTML文件添加 Referrer Policy meta 标签
    
    Parameters
    ----------
    html_file : str
        HTML文件路径
    
    Returns
    -------
    bool
        是否成功修复
    """
    try:
        # 读取HTML
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 检查是否已经有 referrer meta 标签
        if 'name="referrer"' in html_content or 'name=\'referrer\'' in html_content:
            logger.debug(f"   已有 referrer 标签，跳过: {html_file}")
            return False
        
        # 使用 BeautifulSoup 解析
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找 head 标签
        head = soup.find('head')
        if not head:
            logger.warning(f"   未找到 <head> 标签: {html_file}")
            return False
        
        # 创建 meta 标签
        meta_tag = soup.new_tag('meta', attrs={
            'name': 'referrer',
            'content': 'no-referrer'
        })
        
        # 插入到 head 的开头
        if head.contents:
            head.insert(0, meta_tag)
            head.insert(1, soup.new_string('\n    '))
        else:
            head.append(meta_tag)
        
        # 保存修改后的HTML
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        return True
        
    except Exception as e:
        logger.error(f"   处理失败: {e}")
        return False

def fix_all_html_files(root_dir='articles_html'):
    """
    批量修复所有HTML文件
    
    Parameters
    ----------
    root_dir : str
        根目录
    """
    logger.info(f"🔧 开始修复 {root_dir} 目录下的HTML文件...")
    
    total = 0
    fixed = 0
    skipped = 0
    failed = 0
    
    # 遍历所有HTML文件
    for root, dirs, files in os.walk(root_dir):
        for filename in files:
            if filename.endswith('.html'):
                total += 1
                filepath = os.path.join(root, filename)
                
                # 显示相对路径
                rel_path = os.path.relpath(filepath, root_dir)
                logger.info(f"[{total}] 处理: {rel_path}")
                
                result = fix_html_referrer(filepath)
                if result:
                    fixed += 1
                    logger.info(f"   ✅ 已添加 referrer 标签")
                elif result is False:
                    skipped += 1
                else:
                    failed += 1
    
    # 统计
    logger.info(f"\n{'='*60}")
    logger.info(f"修复完成！")
    logger.info(f"{'='*60}")
    logger.info(f"总文件数: {total}")
    logger.info(f"已修复: {fixed}")
    logger.info(f"已跳过: {skipped}")
    logger.info(f"失败: {failed}")
    logger.info(f"{'='*60}")
    
    if fixed > 0:
        logger.info(f"\n✅ 现在可以通过 HTTP 服务器访问文章，图片应该能正常显示了！")
        logger.info(f"   访问地址: http://localhost:5001/articles/")

if __name__ == '__main__':
    fix_all_html_files()
