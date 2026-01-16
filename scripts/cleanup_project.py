# coding: utf-8
"""
项目清理脚本
整理项目结构，移除临时文件
"""
import os
import shutil

def cleanup():
    """清理项目临时文件"""
    # 需要清理的目录/文件模式
    cleanup_patterns = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '.pytest_cache',
        '*.egg-info',
    ]
    
    cleaned = []
    
    for root, dirs, files in os.walk('.'):
        # 跳过虚拟环境和git目录
        if '.venv' in root or 'venv' in root or '.git' in root:
            continue
        
        # 清理 __pycache__ 目录
        for d in dirs:
            if d == '__pycache__':
                path = os.path.join(root, d)
                try:
                    shutil.rmtree(path)
                    cleaned.append(path)
                    print(f"✅ 已删除: {path}")
                except Exception as e:
                    print(f"❌ 删除失败: {path} - {e}")
        
        # 清理 .pyc 文件
        for f in files:
            if f.endswith('.pyc') or f.endswith('.pyo'):
                path = os.path.join(root, f)
                try:
                    os.remove(path)
                    cleaned.append(path)
                    print(f"✅ 已删除: {path}")
                except Exception as e:
                    print(f"❌ 删除失败: {path} - {e}")
    
    print(f"\n清理完成，共删除 {len(cleaned)} 个文件/目录")

if __name__ == '__main__':
    cleanup()
