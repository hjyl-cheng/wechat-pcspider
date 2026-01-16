# coding: utf-8
"""
微信公众号文章数据获取 API 服务
功能：
1. 提供 RESTful API 接口
2. 接收公众号名称、文章URL、获取时间
3. 自动化微信PC端操作（Windows）
4. 返回文章统计数据（JSON格式）
API端点：
- POST /api/fetch_article - 获取单篇文章数据
- POST /api/fetch_articles - 批量获取文章数据
- GET /api/health - 健康检查
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
import threading
import logging
import warnings
# 忽略 urllib3 的 OpenSSL 警告（兼容性问题）
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')
import signal
import atexit
# 导入现有模块
from params.new_wechat_config import COOKIE
from wechatarticles import ArticlesInfo
from smart_batch_fetch import (
    extract_appmsg_token_from_cookie,
    extract_biz_from_url,
    fetch_articles_from_profile,
    get_article_stats,
    download_article_html
)
# 导入数据库模块
from database import test_connection, init_db
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
# 导入微信自动化模块
from wechat_automation import auto_open_article_in_wechat
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求
# 全局变量
proxy_process = None
proxy_lock = threading.Lock()
class WeChatAutomation:
    """微信自动化操作类（使用pywinauto）"""
    
    @staticmethod
    def activate_wechat():
        """
        激活微信窗口（Windows版本）
        """
        try:
            logger.info("🔍 激活微信窗口...")
            from pywinauto import Application, findwindows
            
            # 查找微信窗口
            wechat_windows = findwindows.find_elements(title_re=".*微信.*", class_name="WeChatMainWndForPC")
            
            if not wechat_windows:
                logger.error("❌ 未找到微信窗口，请确保微信已启动")
                return False
            
            # 连接到微信应用
            app = Application().connect(handle=wechat_windows[0].handle)
            
            # 激活微信窗口
            wechat_window = app.window(handle=wechat_windows[0].handle)
            if wechat_window.is_minimized():
                wechat_window.restore()
            
            wechat_window.set_focus()
            
            time.sleep(1)  # 等待窗口激活
            logger.info("✅ 微信窗口已激活")
            return True
            
        except Exception as e:
            logger.error(f"❌ 激活微信失败: {e}")
            return False
    
    @staticmethod
    def open_file_transfer():
        """
        使用pywinauto打开微信文件传输助手
        """
        try:
            from pywinauto import Application, findwindows, keyboard
            import pyperclip
            
            logger.info("🔍 正在打开文件传输助手...")
            
            # 1. 激活微信
            if not WeChatAutomation.activate_wechat():
                return False
            
            # 2. 使用快捷键 Ctrl+F 打开搜索（Windows快捷键）
            logger.info("   按下 Ctrl+F 打开搜索...")
            keyboard.send_keys('^f')
            time.sleep(1.5)
            
            # 3. 输入"文件传输助手"
            logger.info("   输入'文件传输助手'...")
            pyperclip.copy("文件传输助手")
            time.sleep(0.3)
            keyboard.send_keys('^v')
            time.sleep(1.2)
            
            # 4. 按回车打开对话
            logger.info("   按回车打开对话...")
            keyboard.send_keys('{ENTER}')
            time.sleep(2)
            
            logger.info("✅ 成功打开文件传输助手")
            return True
            
        except ImportError:
            logger.error("❌ 请先安装 pywinauto 和 pyperclip: pip install pywinauto pyperclip")
            return False
        except Exception as e:
            logger.error(f"❌ 打开文件传输助手失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def send_and_open_article(article_url):
        """发送文章链接到文件传输助手并打开"""
        try:
            from pywinauto import keyboard
            import pyperclip
            
            logger.info(f"📤 发送文章链接: {article_url[:50]}...")
            
            # 1. 复制文章链接到剪贴板
            logger.info("   复制链接到剪贴板...")
            pyperclip.copy(article_url)
            time.sleep(0.3)
            
            # 2. 粘贴（Ctrl+V）
            logger.info("   粘贴链接...")
            keyboard.send_keys('^v')
            time.sleep(0.8)
            
            # 3. 发送（回车）
            logger.info("   发送链接...")
            keyboard.send_keys('{ENTER}')
            time.sleep(3)  # 等待消息发送完成和链接卡片渲染
            
            # 4. 使用键盘导航打开链接（更可靠的方式）
            logger.info("   使用键盘导航打开链接...")
            
            # 方法1：按上箭头选中最后一条消息（刚发送的链接）
            logger.info("   按上箭头选中链接消息...")
            keyboard.send_keys('{UP}')
            time.sleep(0.5)
            
            # 按回车打开链接
            logger.info("   按回车打开链接...")
            keyboard.send_keys('{ENTER}')
            time.sleep(3)  # 等待文章页面加载
            
            logger.info("✅ 成功发送并打开文章")
            return True
            
        except ImportError:
            logger.error("❌ 请先安装 pywinauto 和 pyperclip: pip install pywinauto pyperclip")
            return False
        except Exception as e:
            logger.error(f"❌ 发送文章失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def auto_open_article_in_wechat(article_url):
        """自动在微信中打开文章（完整流程）"""
        logger.info(f"🤖 开始自动化操作: 在微信中打开文章")
        
        try:
            # 1. 打开文件传输助手
            if not WeChatAutomation.open_file_transfer():
                logger.error("❌ 打开文件传输助手失败")
                return False
            
            time.sleep(1)
            
            # 2. 发送并打开文章
            if not WeChatAutomation.send_and_open_article(article_url):
                logger.error("❌ 发送文章失败")
                return False
            
            logger.info("✅ 文章已在微信中打开，等待参数捕获...")
            return True
            
        except Exception as e:
            logger.error(f"❌ 自动化操作失败: {e}")
            import traceback
            traceback.print_exc()
            return False
class ProxyManager:
    """代理管理器"""
    
    @staticmethod
    def set_system_proxy(enable=True, port=8888):
        """
        设置 Windows 系统代理
        
        Parameters
        ----------
        enable : bool
            True 启用代理，False 禁用代理
        port : int
            代理端口
        """
        try:
            import winreg
            
            if enable:
                logger.info(f"🌐 设置系统代理: 127.0.0.1:{port}")
                
                # 设置注册表值
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 
                                   0, winreg.KEY_SET_VALUE)
                
                # 启用代理
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                # 设置代理服务器
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"127.0.0.1:{port}")
                
                winreg.CloseKey(key)
                
                # 通知系统代理设置更改
                import ctypes
                internet_set_option = ctypes.windll.wininet.InternetSetOptionW
                internet_set_option(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
                internet_set_option(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH
                
                logger.info("✅ 系统代理已设置")
            else:
                logger.info("🌐 关闭系统代理")
                
                # 设置注册表值
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 
                                   0, winreg.KEY_SET_VALUE)
                
                # 禁用代理
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                
                winreg.CloseKey(key)
                
                # 通知系统代理设置更改
                import ctypes
                internet_set_option = ctypes.windll.wininet.InternetSetOptionW
                internet_set_option(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
                internet_set_option(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH
                
                logger.info("✅ 系统代理已关闭")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ 设置系统代理失败: {e}")
            return False
    
    @staticmethod
    def start_proxy_and_capture(article_url, biz=None, timeout=120):
        """
        启动代理服务器并捕获参数（参考 smart_batch_auto.py 的正确流程）
        
        流程：
        1. 设置全局系统代理
        2. 启动代理服务器（不传参数，自动检测BIZ）
        3. 执行微信自动化操作
        4. 等待参数捕获完成（检测 params/biz_{BIZ}/ 目录）
        5. 停止代理并关闭系统代理
        
        Parameters
        ----------
        article_url : str
            文章URL，用于在微信中打开
        biz : str, optional
            公众号BIZ，如果提供则不再从URL提取
        timeout : int
            超时时间（秒）
        
        Returns
        -------
        bool
            是否成功捕获参数
        """
        global proxy_process
        
        with proxy_lock:
            if proxy_process is not None:
                logger.warning("⚠️  代理服务器已在运行")
                return False
            
            try:
                # 获取BIZ（如果没提供则从URL提取）
                if not biz:
                    logger.info("   从URL提取BIZ...")
                    biz = extract_biz_from_url(article_url)
                    if not biz:
                        logger.error("❌ 无法从URL提取BIZ")
                        return False
                    logger.info(f"   ✅ 提取到BIZ: {biz}")
                else:
                    logger.info(f"   使用已知BIZ: {biz}")
                
                # 参数文件路径（参考 capture_new_wechat.py 的保存逻辑）
                biz_dir = f"params/biz_{biz}"
                params_file = f"{biz_dir}/config.py"
                json_file = f"{biz_dir}/params.json"
                
                # 步骤1: 设置全局系统代理
                logger.info("🚀 步骤1: 设置全局系统代理")
                if not ProxyManager.set_system_proxy(enable=True, port=8888):
                    logger.error("❌ 设置系统代理失败")
                    return False
                
                # 步骤2: 启动代理服务器（使用multiprocessing）
                logger.info(f"🚀 步骤2: 启动代理服务器（multiprocessing）")
                
                from multiprocessing import Process, Queue
                from capture_process import run_capture_process
                
                # 创建通信队列
                command_queue = Queue()
                result_queue = Queue()
                
                # 创建并启动捕获进程
                capture_proc = Process(
                    target=run_capture_process,
                    args=(command_queue, result_queue),
                    daemon=True  # 守护进程，主进程退出时自动结束
                )
                capture_proc.start()
                logger.info(f"   捕获进程已启动 (PID: {capture_proc.pid})")
                
                # 保存到全局变量（用于cleanup）
                proxy_process = capture_proc
                
                # 定义状态
                is_listening = False
                
                # 循环等待启动消息（最多15秒）
                startup_timeout = 15
                startup_start = time.time()
                
                while time.time() - startup_start < startup_timeout:
                    try:
                        # 尝试获取消息
                        msg = result_queue.get(timeout=1.0)
                        msg_type = msg.get('type')
                        msg_status = msg.get('status')
                        logger.info(f"   [捕获进程] {msg.get('message', '')}")
                        
                        if msg_status == 'listening':
                            is_listening = True
                            break
                        
                        if msg_type == 'error':
                            logger.error(f"❌ 捕获进程出错: {msg.get('message')}")
                            if 'traceback' in msg:
                                logger.error(f"   {msg['traceback']}")
                            capture_proc.terminate()
                            proxy_process = None
                            return False
                            
                    except:
                        # Queue暂时为空
                        pass
                        
                    if not capture_proc.is_alive():
                        logger.error("❌ 捕获进程意外退出")
                        proxy_process = None
                        return False
                
                if not is_listening:
                    logger.warning(f"⚠️  未收到监听确认，尝试直接检查端口...")
                
                # 验证端口
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                max_retries = 5 # 增加重试次数
                for i in range(max_retries):
                    try:
                        result = sock.connect_ex(('127.0.0.1', 8888))
                        if result == 0:
                            logger.info("✅ 代理服务器已启动，端口 8888 正在监听")
                            break
                        else:
                            if i < max_retries - 1:
                                logger.info(f"   端口未监听，等待... ({i+1}/{max_retries})")
                                time.sleep(2)
                            else:
                                logger.error(f"❌ 端口 8888 未在监听")
                                capture_proc.terminate()
                                capture_proc.join(timeout=2)
                                proxy_process = None
                                return False
                    finally:
                        try:
                            sock.close()
                        except:
                            pass
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                sock.close()
                
                # 步骤3: 执行微信自动化操作
                logger.info("🚀 步骤3: 执行微信自动化操作")
                if not auto_open_article_in_wechat(article_url):
                    logger.error("❌ 微信自动化操作失败")
                    capture_proc.terminate()
                    capture_proc.join(timeout=2)
                    proxy_process = None
                    return False
                
                logger.info("✅ 文章已在微信中打开，等待参数捕获...")
                
                # 步骤4: 等待参数捕获完成（通过Queue）
                logger.info(f"🚀 步骤4: 等待参数捕获（最多{timeout}秒）...")
                logger.info(f"   监控BIZ: {biz}")
                logger.info(f"   通过Queue接收消息...")
                
                start_time = time.time()
                last_log_time = start_time
                log_interval = 10
                
                while time.time() - start_time < timeout:
                    current_time = time.time()
                    elapsed = int(current_time - start_time)
                    
                    # 定期打印等待日志
                    if current_time - last_log_time >= log_interval:
                        logger.info(f"   等待中... ({elapsed}/{timeout}秒)")
                        last_log_time = current_time
                    
                    # 从Queue接收消息
                    try:
                        msg = result_queue.get(timeout=0.5)
                        msg_type = msg.get('type', 'unknown')
                        msg_status = msg.get('status', '')
                        msg_text = msg.get('message', '')
                        
                        logger.info(f"   [捕获进程] {msg_text}")
                        
                        # 检查是否完成
                        if msg_type == 'complete' and msg_status == 'success':
                            logger.info(f"✅ 参数捕获成功！")
                            logger.info(f"   BIZ: {msg.get('biz', biz)}")
                            logger.info(f"   已耗时: {elapsed}秒")
                            
                            # 等待数据库写入
                            time.sleep(2)
                            
                            # 终止捕获进程
                            capture_proc.terminate()
                            capture_proc.join(timeout=2)
                            proxy_process = None
                            
                            return True
                        
                        # 检查错误
                        if msg_type == 'error':
                            logger.error(f"❌ 捕获失败: {msg_text}")
                            if 'traceback' in msg:
                                logger.error(f"   详情:\n{msg['traceback']}")
                            capture_proc.terminate()
                            capture_proc.join(timeout=2)
                            proxy_process = None
                            return False
                        
                    except:
                        # Queue为空，继续等待
                        pass
                    
                    # 检查进程是否还活着
                    if not capture_proc.is_alive():
                        logger.warning(f"   捕获进程已退出")
                        # 检查文件作为备用
                        if os.path.exists(params_file):
                            logger.info(f"✅ 参数文件已创建: {params_file}")
                            proxy_process = None
                            return True
                        else:
                            logger.error(f"❌ 捕获失败，参数文件不存在")
                            proxy_process = None
                            return False
                
                logger.error(f"❌ 参数捕获超时（{timeout}秒）")
                
                # 超时，终止进程
                capture_proc.terminate()
                capture_proc.join(timeout=2)
                proxy_process = None
                
                return False
                
            except Exception as e:
                logger.error(f"❌ 启动代理失败: {e}")
                traceback.print_exc()
                return False
            finally:
                # 步骤5: 清理代理设置（带超时保护）
                logger.info("🚀 步骤5: 清理代理设置")
                
                # 快速终止进程（不等待太久）
                if 'capture_proc' in dir() and capture_proc is not None:
                    try:
                        if capture_proc.is_alive():
                            capture_proc.terminate()
                            capture_proc.join(timeout=1)
                        logger.info("   ✅ 捕获进程已停止")
                    except:
                        pass
                
                proxy_process = None
                
                # 关闭系统代理
                try:
                    ProxyManager.set_system_proxy(enable=False)
                    logger.info("   ✅ 系统代理已关闭")
                except Exception as e:
                    logger.warning(f"   关闭系统代理失败: {e}")
                
                logger.info("✅ 清理完成")
    
    @staticmethod
    def stop_proxy():
        """停止代理服务器 - 支持multiprocessing.Process"""
        global proxy_process
        
        with proxy_lock:
            if proxy_process is not None:
                try:
                    logger.info("   正在停止捕获进程...")
                    
                    # 检查是否是Process对象
                    if hasattr(proxy_process, 'is_alive'):
                        # multiprocessing.Process
                        if proxy_process.is_alive():
                            proxy_process.terminate()
                            proxy_process.join(timeout=3)
                            if proxy_process.is_alive():
                                logger.warning("   进程未响应，强制终止...")
                                proxy_process.kill()
                                proxy_process.join(timeout=1)
                        logger.info("✅ 捕获进程已停止")
                    else:
                        # subprocess.Popen (兼容旧代码)
                        proxy_process.terminate()
                        try:
                            proxy_process.wait(timeout=3)
                        except:
                            proxy_process.kill()
                        logger.info("✅ 代理进程已停止")
                        
                except Exception as e:
                    logger.error(f"   停止进程失败: {e}")
                finally:
                    proxy_process = None
            
            # 清理8888端口（如果有残留进程）
            try:
                import subprocess
                # Windows使用netstat查找占用8888端口的进程
                result = subprocess.run(
                    ['netstat', '-ano', '|', 'findstr', ':8888'],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) > 4:
                            pid = parts[-1]
                            
                            try:
                                # 查找进程名，确保是Python进程
                                process_info = subprocess.run(
                                    ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                                    capture_output=True,
                                    text=True,
                                    timeout=2
                                )
                                
                                if 'python.exe' in process_info.stdout.lower():
                                    logger.info(f"   清理残留Python进程: {pid}")
                                    subprocess.run(['taskkill', '/PID', pid, '/F'], timeout=2)
                            except:
                                pass
                                
            except Exception as e:
                logger.debug(f"   清理端口时出错: {e}")
# ==================== API 端点 ====================
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'WeChat Articles API'
    })

@app.route('/articles/<path:filepath>')
def serve_article(filepath):
    """
    提供静态HTML文件访问
    
    示例：
    http://localhost:5001/articles/涂磊/2025-12-11/文章标题.html
    """
    try:
        # 构建完整路径用于调试
        full_path = os.path.join('articles_html', filepath)
        logger.info(f"📄 请求文件: {filepath}")
        logger.info(f"   完整路径: {full_path}")
        logger.info(f"   文件存在: {os.path.exists(full_path)}")
        
        # 使用 send_from_directory，它会自动处理路径
        response = send_from_directory('articles_html', filepath)
        
        # 设置 Referrer Policy 响应头，防止图片防盗链
        response.headers['Referrer-Policy'] = 'no-referrer'
        
        return response
    except Exception as e:
        logger.error(f"❌ 访问文件失败: {e}")
        logger.error(f"   请求路径: {filepath}")
        
        # 尝试列出可用文件
        try:
            parts = filepath.split('/')
            if len(parts) >= 2:
                account = parts[0]
                date = parts[1] if len(parts) > 1 else ''
                check_path = os.path.join('articles_html', account, date)
                if os.path.exists(check_path):
                    available = os.listdir(check_path)
                    logger.info(f"   该目录下的文件: {available}")
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': f'文件不存在: {filepath}',
            'hint': '请使用 /articles/ 查看所有可用文章'
        }), 404

@app.route('/articles_html/<path:filepath>')
def serve_article_alt(filepath):
    """
    备用路径：/articles_html/...
    重定向到 /articles/...
    """
    from flask import redirect
    return redirect(f'/articles/{filepath}', code=301)

@app.route('/articles/')
@app.route('/articles')
def list_articles():
    """
    列出所有可用的文章HTML文件
    
    返回文章列表的JSON格式
    """
    try:
        articles = []
        articles_dir = 'articles_html'
        
        if not os.path.exists(articles_dir):
            return jsonify({
                'success': True,
                'articles': [],
                'total': 0
            })
        
        # 遍历目录结构
        for account_name in os.listdir(articles_dir):
            account_path = os.path.join(articles_dir, account_name)
            if not os.path.isdir(account_path):
                continue
            
            for date_folder in os.listdir(account_path):
                date_path = os.path.join(account_path, date_folder)
                if not os.path.isdir(date_path):
                    continue
                
                for filename in os.listdir(date_path):
                    if filename.endswith('.html'):
                        file_path = os.path.join(account_name, date_folder, filename)
                        file_size = os.path.getsize(os.path.join(date_path, filename))
                        
                        articles.append({
                            'account': account_name,
                            'date': date_folder,
                            'title': filename.replace('.html', ''),
                            'path': file_path,
                            'url': f'/articles/{file_path}',
                            'size': file_size
                        })
        
        # 按日期排序
        articles.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            'success': True,
            'articles': articles,
            'total': len(articles)
        })
        
    except Exception as e:
        logger.error(f"❌ 列出文章失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@app.route('/api/fetch_article', methods=['POST'])
def fetch_article():
    """
    获取单篇文章数据
    
    请求体：
    {
        "account_name": "公众号名称",
        "article_url": "文章URL",
        "fetch_time": "获取时间（可选）"
    }
    
    返回：
    {
        "success": true,
        "data": {
            "title": "文章标题",
            "url": "文章URL",
            "read_count": 10000,
            "like_count": 100,
            ...
        }
    }
    """
    try:
        # 解析请求
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        account_name = data.get('account_name')
        article_url = data.get('article_url')
        fetch_time = data.get('fetch_time', datetime.now().isoformat())
        
        if not article_url:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: article_url'
            }), 400
        
        logger.info(f"📥 收到请求: 公众号={account_name}, URL={article_url}")
        
        # 1. 提取BIZ
        biz = extract_biz_from_url(article_url)
        if not biz:
            # 检查是否是验证码页面
            error_msg = '无法从URL提取BIZ'
            if 'wappoc_appmsgcaptcha' in article_url or 'captcha' in article_url.lower():
                error_msg = '该文章需要验证码，请尝试：1) 更换其他文章URL，2) 在微信PC端手动打开文章后重试'
            else:
                error_msg = '无法从URL提取BIZ，请检查URL格式或尝试其他文章'
            
            logger.error(f"❌ {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # 2. 检查参数文件是否存在且有效
        biz_dir = f"params/biz_{biz}"
        params_file = f"{biz_dir}/config.py"
        need_capture = False
        
        if not os.path.exists(params_file):
            logger.info(f"⚠️  参数文件不存在: {params_file}")
            need_capture = True
        else:
            # 验证参数有效性
            logger.info(f"🔍 检查参数文件: {params_file}")
            try:
                # 动态导入BIZ专属配置
                import importlib.util
                spec = importlib.util.spec_from_file_location("biz_config", params_file)
                biz_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(biz_config)
                
                cookie = biz_config.COOKIE
                key = biz_config.KEY
                pass_ticket = biz_config.PASS_TICKET
                uin = biz_config.UIN
                
                if not cookie or not key or not pass_ticket or not uin:
                    logger.warning(f"⚠️  参数文件缺少必要字段")
                    need_capture = True
                else:
                    # 提取 appmsg_token
                    import re
                    match = re.search(r'appmsg_token=([^;]+)', cookie)
                    if not match:
                        logger.warning(f"⚠️  Cookie中缺少appmsg_token")
                        need_capture = True
                    else:
                        appmsg_token = match.group(1)
                        
                        # 测试参数是否有效（使用当前BIZ）
                        logger.info(f"🔍 验证参数有效性...")
                        logger.info(f"   使用BIZ: {biz}")
                        try:
                            import requests
                            
                            # 使用当前BIZ进行验证（而不是固定的测试BIZ）
                            test_url = (
                                f"https://mp.weixin.qq.com/mp/profile_ext?"
                                f"action=getmsg&"
                                f"__biz={biz}&"
                                f"f=json&"
                                f"offset=0&"
                                f"count=1&"
                                f"is_ok=1&"
                                f"scene=124&"
                                f"uin={uin}&"
                                f"key={key}&"
                                f"pass_ticket={pass_ticket}&"
                                f"wxtoken=&"
                                f"appmsg_token={appmsg_token}&"
                                f"x5=0"
                            )
                            
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                'Cookie': cookie,
                                'Referer': f'https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={biz}&scene=124',
                            }
                            
                            response = requests.get(test_url, headers=headers, timeout=10)
                            data = response.json()
                            
                            # 检查返回结果
                            if data.get('ret') == -3 or 'no session' in str(data.get('errmsg', '')).lower():
                                logger.warning(f"⚠️  参数已失效（API返回: no session）")
                                need_capture = True
                            elif data.get('ret') != 0:
                                error_msg = data.get('errmsg', 'Unknown error')
                                logger.warning(f"⚠️  API返回错误: {error_msg}")
                                # 其他错误也认为参数可能失效
                                need_capture = True
                            else:
                                logger.info(f"✅ 参数有效（API测试通过）")
                                # 参数有效，不需要捕获
                        except Exception as e:
                            logger.warning(f"⚠️  参数验证失败: {e}")
                            need_capture = True
                        
            except Exception as e:
                logger.warning(f"⚠️  读取参数文件失败: {e}")
                need_capture = True
        
        # 3. 如果需要，启动代理并捕获参数
        if need_capture:
            logger.info(f"🚀 开始参数捕获流程...")
            
            # 启动代理并捕获参数（正确流程：先代理，后自动化）
            if not ProxyManager.start_proxy_and_capture(article_url, timeout=120):
                return jsonify({
                    'success': False,
                    'error': '参数捕获失败，请确保微信已正常运行'
                }), 500
        
        # 4. 加载参数
        try:
            # 重新加载BIZ专属配置
            import importlib.util
            spec = importlib.util.spec_from_file_location("biz_config", params_file)
            biz_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(biz_config)
            
            cookie = biz_config.COOKIE
            appmsg_token = extract_appmsg_token_from_cookie(cookie)
            
            if not appmsg_token:
                return jsonify({
                    'success': False,
                    'error': 'Cookie中缺少appmsg_token'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'读取参数文件失败: {str(e)}'
            }), 500
        
        
        # 5. 获取文章统计数据
        logger.info(f"📊 获取文章统计数据...")
        
        try:
            # 重要：get_article_stats 需要长链接（包含 __biz, mid, idx, sn 等参数）
            # 如果是短链接，需要先转换
            final_article_url = article_url
            
            logger.info(f"   原始URL: {article_url}")
            logger.info(f"   是否包含/s/: {'/s/' in article_url}")
            logger.info(f"   是否包含__biz=: {'__biz=' in article_url}")
            
            if '/s/' in article_url and '__biz=' not in article_url:
                logger.info(f"   检测到短链接，正在转换为长链接...")
                try:
                    import requests
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
                        'Cookie': cookie,
                    }
                    logger.info(f"   发送请求到: {article_url}")
                    response = requests.get(article_url, headers=headers, allow_redirects=True, timeout=15)
                    final_article_url = response.url
                    logger.info(f"   响应状态码: {response.status_code}")
                    logger.info(f"   最终URL: {final_article_url}")
                    logger.info(f"   URL长度: {len(final_article_url)}")
                    
                    # 检查是否真的转换成功
                    if '__biz=' in final_article_url:
                        logger.info(f"   ✅ 成功转换为长链接")
                    else:
                        logger.warning(f"   ⚠️  转换后仍然是短链接")
                        # 尝试从响应内容中提取
                        logger.info(f"   尝试从响应内容中提取长链接...")
                        import re
                        content = response.text
                        # 查找 var msg_link
                        match = re.search(r'var\s+msg_link\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            final_article_url = match.group(1).replace('\\/', '/')
                            logger.info(f"   从msg_link提取到: {final_article_url[:100]}...")
                except Exception as e:
                    logger.error(f"   ❌ 转换长链接失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.info(f"   已经是长链接，无需转换")
            
            logger.info(f"   最终使用的URL: {final_article_url[:150]}...")
            
            articles_info = ArticlesInfo(appmsg_token=appmsg_token, cookie=cookie)
            stats = get_article_stats(final_article_url, articles_info)
            
            if not stats or not stats.get('success'):
                error_msg = stats.get('error', '未知错误') if stats else '返回值为空'
                logger.error(f"❌ 获取文章统计数据失败: {error_msg}")
                logger.error(f"   使用的URL: {final_article_url[:150]}...")
                return jsonify({
                    'success': False,
                    'error': f'获取文章统计数据失败: {error_msg}'
                }), 500
        except Exception as e:
            logger.error(f"❌ 获取文章统计数据异常: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'获取文章统计数据异常: {str(e)}'
            }), 500
        
        # 6. 下载HTML（可选）
        if stats.get('title') and stats.get('publish_date'):
            html_path = download_article_html(
                article_url,
                stats['title'],
                stats['publish_date']
            )
            if html_path:
                stats['local_html_path'] = html_path
        
        # 9. 添加元数据
        result = {
            'account_name': account_name,
            'fetch_time': fetch_time,
            'biz': biz,
            **stats
        }
        
        logger.info(f"✅ 成功获取文章数据: {stats.get('title')}")
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"❌ 处理请求时出错: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@app.route('/api/fetch_articles', methods=['POST'])
def fetch_articles():
    """
    批量获取文章数据
    
    请求体：
    {
        "account_name": "公众号名称",
        "articles": [
            {
                "url": "文章URL1",
                "fetch_time": "获取时间（可选）"
            },
            {
                "url": "文章URL2",
                "fetch_time": "获取时间（可选）"
            }
        ]
    }
    
    返回：
    {
        "success": true,
        "data": [
            { ... },
            { ... }
        ],
        "summary": {
            "total": 2,
            "success": 2,
            "failed": 0
        }
    }
    """
    try:
        # 解析请求
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        account_name = data.get('account_name')
        articles = data.get('articles', [])
        
        if not articles:
            return jsonify({
                'success': False,
                'error': '文章列表不能为空'
            }), 400
        
        logger.info(f"📥 收到批量请求: 公众号={account_name}, 文章数={len(articles)}")
        
        results = []
        success_count = 0
        failed_count = 0
        
        # 处理每篇文章
        for idx, article in enumerate(articles, 1):
            article_url = article.get('url')
            fetch_time = article.get('fetch_time', datetime.now().isoformat())
            
            if not article_url:
                logger.warning(f"⚠️  跳过第{idx}篇文章：缺少URL")
                failed_count += 1
                continue
            
            logger.info(f"📄 处理第{idx}/{len(articles)}篇文章...")
            
            # 调用单篇文章获取逻辑
            try:
                # 这里可以复用fetch_article的逻辑
                # 为了简化，我们直接调用内部函数
                biz = extract_biz_from_url(article_url)
                if not biz:
                    logger.warning(f"⚠️  跳过第{idx}篇文章：无法提取BIZ")
                    failed_count += 1
                    continue
                
                # 检查并捕获参数（只在第一次需要）
                params_file = f"params/{biz}.json"
                if not os.path.exists(params_file) and idx == 1:
                    logger.info(f"⚠️  参数文件不存在，需要捕获参数")
                    if not ProxyManager.start_proxy_and_capture(article_url, timeout=120):
                        logger.error(f"❌ 参数捕获失败")
                        failed_count += 1
                        continue
                
                # 加载参数并获取数据
                with open(params_file, 'r', encoding='utf-8') as f:
                    params = json.load(f)
                
                appmsg_token = params.get('appmsg_token')
                cookie = params.get('cookie', COOKIE)
                articles_info = ArticlesInfo(appmsg_token=appmsg_token, cookie=cookie)
                
                stats = get_article_stats(article_url, articles_info)
                
                if stats:
                    # 下载HTML
                    if stats.get('title') and stats.get('publish_date'):
                        html_path = download_article_html(
                            article_url,
                            stats['title'],
                            stats['publish_date']
                        )
                        if html_path:
                            stats['local_html_path'] = html_path
                    
                    result = {
                        'account_name': account_name,
                        'fetch_time': fetch_time,
                        'biz': biz,
                        **stats
                    }
                    results.append(result)
                    success_count += 1
                    logger.info(f"✅ 第{idx}篇文章获取成功")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️  第{idx}篇文章获取失败")
                
                # 延迟，避免请求过快
                if idx < len(articles):
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"❌ 第{idx}篇文章处理失败: {e}")
                failed_count += 1
        
        return jsonify({
            'success': True,
            'data': results,
            'summary': {
                'total': len(articles),
                'success': success_count,
                'failed': failed_count
            }
        })
        
    except Exception as e:
        logger.error(f"❌ 批量处理请求时出错: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
@app.route('/api/stop_proxy', methods=['POST'])
def stop_proxy():
    """手动停止代理服务器"""
    ProxyManager.stop_proxy()
    return jsonify({
        'success': True,
        'message': '代理服务器已停止'
    })
def cleanup_on_exit():
    """程序退出时的清理函数"""
    try:
        logger.info("🧹 清理资源...")
        # 设置超时，不要卡太久
        import signal
        def timeout_handler(signum, frame):
            logger.warning("⚠️  清理超时，强制退出")
            os._exit(1)
        
        # 设置5秒超时
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)
        
        try:
            ProxyManager.stop_proxy()
            ProxyManager.set_system_proxy(enable=False)
            logger.info("✅ 清理完成")
        finally:
            signal.alarm(0)  # 取消超时
    except Exception as e:
        logger.error(f"清理时出错: {e}")
def signal_handler(sig, frame):
    """信号处理器"""
    logger.info(f"\n\n⚠️  收到中断信号 ({sig})")
    
    # 快速清理并退出
    try:
        ProxyManager.set_system_proxy(enable=False)
    except:
        pass
    
    logger.info("👋 再见！")
    os._exit(0)  # 强制退出，不等待线程
if __name__ == '__main__':
    # 注册退出清理函数
    atexit.register(cleanup_on_exit)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill命令
    
    # 确保必要的目录存在
    os.makedirs('params', exist_ok=True)
    os.makedirs('articles_html', exist_ok=True)
    
    # 初始化数据库
    logger.info("🗄️  初始化数据库...")
    try:
        from database import test_connection, init_db
        if test_connection():
            init_db()
            logger.info("✅ 数据库初始化成功")
        else:
            logger.warning("⚠️  数据库连接失败，将使用文件存储")
    except Exception as e:
        logger.warning(f"⚠️  数据库初始化失败: {e}，将使用文件存储")
    
    # 注册新的API端点（使用数据库缓存）
    from api_endpoints_new import fetch_article_with_cache, fetch_articles_filtered
    app.add_url_rule('/api/v2/fetch_article', 'fetch_article_v2', fetch_article_with_cache, methods=['POST'])
    app.add_url_rule('/api/v2/fetch_articles_filtered', 'fetch_articles_filtered', fetch_articles_filtered, methods=['POST'])
    
    # 注册智能API端点（完全模拟smart_batch_auto.py + 智能增量）
    from api_endpoints_smart import fetch_articles_smart
    app.add_url_rule('/api/fetch_articles_smart', 'fetch_articles_smart', fetch_articles_smart, methods=['POST'])
    
    # 启动服务器
    logger.info("🚀 启动微信公众号文章API服务...")
    logger.info("📍 服务地址: http://localhost:5001")
    logger.info("📖 API文档:")
    logger.info("   - GET  /api/health - 健康检查")
    logger.info("   - POST /api/fetch_article - 获取单篇文章（旧版）")
    logger.info("   - POST /api/v2/fetch_article - 获取单篇文章（新版，使用数据库缓存）")
    logger.info("   - POST /api/v2/fetch_articles_filtered - 批量获取文章（带过滤）")
    logger.info("   - POST /api/fetch_articles - 批量获取文章（旧版）")
    logger.info("   - POST /api/fetch_articles_smart - 智能批量获取（增量+自动捕获）")
    logger.info("   - POST /api/stop_proxy - 停止代理服务器")
    logger.info("📄 静态文件服务:")
    logger.info("   - GET  /articles/ - 列出所有文章")
    logger.info("   - GET  /articles/<path> - 访问HTML文章")
    
    try:
        # 注意：禁用reloader避免捕获参数时Flask重启
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=True,
            threaded=True,
            use_reloader=False  # 禁用自动重载，避免参数文件变化触发重启
        )
    except KeyboardInterrupt:
        logger.info("\n\n👋 用户中断")
    finally:
        cleanup_on_exit()
