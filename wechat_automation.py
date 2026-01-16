#!/usr/bin/env python
# coding: utf-8
"""
微信自动化操作模块
使用 pywinauto 控制微信 PC 端
"""

import time
import logging
import pyperclip
import win32gui
import win32con
import random
from pywinauto import Application, keyboard

logger = logging.getLogger(__name__)


def find_wechat_window():
    """使用 win32gui 查找微信窗口"""
    try:
        logger.info("查找微信窗口...")
        
        def enum_windows_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                
                # 优先查找微信客户端窗口（类名包含 WeChat）
                if "WeChat" in class_name:
                    results.insert(0, (hwnd, title, class_name))
                elif title and "微信" in title and "Chrome" not in title:
                    results.append((hwnd, title, class_name))
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        if windows:
            wechat_hwnd, title, class_name = windows[0]
            logger.info(f"✅ 找到微信窗口: {title} (类名: {class_name})")
            return wechat_hwnd
        else:
            logger.error("❌ 未找到微信窗口")
            return None
            
    except Exception as e:
        logger.error(f"❌ 查找微信窗口失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def activate_wechat_window(hwnd):
    """激活微信窗口"""
    try:
        logger.info("激活微信窗口...")
        
        # 如果窗口最小化，先恢复
        if win32gui.IsIconic(hwnd):
            logger.info("恢复最小化的窗口...")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
        
        # 使用多种方法尝试激活窗口
        try:
            # 方法1: 直接设置前台窗口
            win32gui.SetForegroundWindow(hwnd)
        except:
            # 方法2: 先显示窗口再设置前台
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.BringWindowToTop(hwnd)
                time.sleep(0.3)
                win32gui.SetForegroundWindow(hwnd)
            except:
                # 方法3: 使用 pywinauto 激活
                try:
                    app = Application(backend="uia").connect(handle=hwnd)
                    window = app.window(handle=hwnd)
                    window.set_focus()
                except Exception as e:
                    logger.warning(f"所有激活方法都失败了，但继续执行: {e}")
        
        time.sleep(1)
        logger.info("✅ 窗口已激活")
        return True
        
    except Exception as e:
        logger.error(f"❌ 激活窗口失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def open_file_transfer_assistant_by_search(hwnd):
    """通过搜索打开文件传输助手"""
    try:
        logger.info("📂 通过搜索打开文件传输助手...")
        
        # 使用 Ctrl+F 打开搜索
        logger.info("   按下 Ctrl+F 打开搜索...")
        keyboard.send_keys('^f')
        time.sleep(1.5)
        
        # 输入"文件"（两个字）
        logger.info("   输入'文件'...")
        pyperclip.copy("文件")
        time.sleep(0.3)
        keyboard.send_keys('^v')
        time.sleep(1.5)
        
        # 按回车打开对话
        logger.info("   按回车打开文件传输助手...")
        keyboard.send_keys('{ENTER}')
        time.sleep(2)
        
        # 点击聊天对话框让它聚焦
        try:
            logger.info("   点击聊天对话框使其聚焦...")
            app = Application(backend="uia").connect(handle=hwnd)
            wechat_window = app.window(handle=hwnd)
            
            # 查找输入框并点击
            input_field = wechat_window.child_window(
                auto_id="chat_input_field",
                control_type="Edit"
            )
            
            if input_field.exists(timeout=2):
                input_field.click_input()
                time.sleep(0.5)
                logger.info("   ✅ 聊天对话框已聚焦")
            else:
                logger.warning("   未找到输入框，跳过聚焦步骤")
        except Exception as e:
            logger.warning(f"   聚焦失败，但继续执行: {e}")
        
        logger.info("✅ 成功打开文件传输助手")
        return True
        
    except Exception as e:
        logger.error(f"❌ 打开文件传输助手失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_link(link_url):
    """发送链接到当前聊天窗口"""
    try:
        logger.info(f"📤 发送链接: {link_url[:50]}...")
        
        # 将链接复制到剪贴板
        logger.info("   复制链接到剪贴板...")
        pyperclip.copy(link_url)
        time.sleep(0.5)
        
        # 粘贴链接到输入框
        logger.info("   粘贴链接到输入框...")
        keyboard.send_keys('^v')
        time.sleep(1)
        
        # 按回车发送
        logger.info("   按回车发送...")
        keyboard.send_keys('{ENTER}')
        
        # 等待2秒让链接发送完成
        logger.info("   等待链接发送完成...")
        time.sleep(2)
        
        logger.info("✅ 链接发送成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 发送链接失败: {e}")
        return False


def open_link_by_url(hwnd, link_url):
    """通过链接URL精确定位并点击打开（直接点击最后一条消息）"""
    try:
        logger.info("🔗 查找并打开最新发送的链接...")
        
        # 直接使用主窗口，不查找独立窗口（更快更可靠）
        app = Application(backend="uia").connect(handle=hwnd)
        wechat_window = app.window(handle=hwnd)
        logger.info("   使用微信主窗口")
        
        try:
            # 查找所有聊天消息元素
            all_messages = wechat_window.descendants(
                class_name="mmui::ChatTextItemView",
                control_type="ListItem"
            )
            
            if all_messages:
                logger.info(f"   找到 {len(all_messages)} 个聊天消息")
                
                # 收集消息的位置信息
                messages_with_pos = []
                for msg in all_messages:
                    try:
                        rect = msg.rectangle()
                        text = msg.window_text()
                        messages_with_pos.append((msg, rect.left, rect.top, text))
                        logger.debug(f"   消息位置: X={rect.left}, Y={rect.top}, Text={text[:50]}...")
                    except:
                        continue
                
                if messages_with_pos:
                    # 按 Y 坐标排序，最大的 Y 值就是最下面的消息
                    messages_with_pos.sort(key=lambda x: x[2])  # 按 Y 坐标排序
                    latest_message = messages_with_pos[-1][0]
                    latest_x = messages_with_pos[-1][1]
                    latest_y = messages_with_pos[-1][2]
                    
                    # 获取消息的宽度，在右侧区域随机点击
                    rect = latest_message.rectangle()
                    # 在消息右侧 60%-80% 的范围内随机选择 X 坐标
                    random_x_ratio = random.uniform(0.6, 0.8)
                    # 在消息 40%-60% 的高度范围内随机选择 Y 坐标
                    random_y_ratio = random.uniform(0.4, 0.6)
                    
                    click_x = rect.left + int(rect.width() * random_x_ratio)
                    click_y = rect.top + int(rect.height() * random_y_ratio)
                    
                    logger.info(f"   随机点击消息右侧（X={click_x}, Y={click_y}）...")
                    latest_message.click_input(coords=(click_x - rect.left, click_y - rect.top))
                    
                    # 随机等待 3-5 秒
                    wait_time = random.uniform(3, 5)
                    logger.info(f"   等待 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)
                    
                    # 按 Ctrl+W 关闭页面
                    logger.info("   按 Ctrl+W 关闭页面...")
                    keyboard.send_keys('^w')
                    time.sleep(1)
                    
                    logger.info("✅ 链接已打开并关闭")
                    return True
                else:
                    logger.warning("   无法获取消息位置")
                    return False
            else:
                logger.warning("   未找到聊天消息")
                return False
                
        except Exception as e:
            logger.warning(f"   打开链接失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"❌ 打开链接失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def auto_open_article_in_wechat(article_url):
    """
    自动在微信中打开文章（完整流程）
    
    Parameters
    ----------
    article_url : str
        文章URL
    
    Returns
    -------
    bool
        是否成功
    """
    logger.info(f"🤖 开始自动化操作: 在微信中打开文章")
    logger.info(f"   文章URL: {article_url[:80]}...")
    
    try:
        # 步骤1: 查找微信窗口
        logger.info("1️⃣  查找微信窗口...")
        wechat_hwnd = find_wechat_window()
        if not wechat_hwnd:
            logger.error("❌ 无法找到微信窗口")
            return False
        
        # 步骤2: 激活微信窗口
        logger.info("2️⃣  激活微信窗口...")
        if not activate_wechat_window(wechat_hwnd):
            logger.error("❌ 无法激活微信窗口")
            return False
        
        # 步骤3: 打开文件传输助手
        logger.info("3️⃣  打开文件传输助手...")
        if not open_file_transfer_assistant_by_search(wechat_hwnd):
            logger.error("❌ 无法打开文件传输助手")
            return False
        
        # 步骤4: 发送链接
        logger.info("4️⃣  发送链接...")
        if not send_link(article_url):
            logger.error("❌ 无法发送链接")
            return False
        
        # 步骤5: 打开链接
        logger.info("5️⃣  打开链接...")
        if not open_link_by_url(wechat_hwnd, article_url):
            logger.error("❌ 无法打开链接")
            return False
        
        logger.info("✅ 文章已在微信中打开，等待参数捕获...")
        return True
        
    except Exception as e:
        logger.error(f"❌ 自动化操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False
