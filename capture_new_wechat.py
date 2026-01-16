# coding: utf-8
"""
新版本 PC 微信参数捕获工具
适配新版本 PC 微信，提取 key、pass_ticket 和 Cookie
"""

import os
import re
import json
import urllib.parse
from datetime import datetime
from wechatarticles.proxy import ReqIntercept, RspIntercept, MitmProxy, ProxyHandle


class NewPCWeChatProxyHandle(ProxyHandle):
    """新版本 PC 微信代理处理器"""
    
    def hook_init(self):
        self.filter_url_lst = ["mp.weixin.qq.com"]


class NewPCWeChatCapture(ReqIntercept, RspIntercept):
    """新版本 PC 微信参数捕获器"""
    
    def __init__(self, server):
        super().__init__(server)
        self.params_dir = "params"
        self._ensure_params_dir()
        self.captured_params = {
            "cookie": None,
            "key": None,
            "pass_ticket": None,
            "uin": None,
            "devicetype": None,
            "clientversion": None,
        }
        self.captured = False
    
    def _ensure_params_dir(self):
        if not os.path.exists(self.params_dir):
            os.makedirs(self.params_dir)
    
    def _get_cookie(self, request):
        headers = request.headers
        return headers.get("Cookie") or headers.get("cookie")
    
    def _extract_params(self, url):
        """从 URL 中提取所有参数"""
        params = {}
        
        # 提取 key
        key_match = re.search(r'[&?]key=([^&]+)', url)
        if key_match:
            params["key"] = urllib.parse.unquote(key_match.group(1))
        
        # 提取 pass_ticket
        pass_ticket_match = re.search(r'[&?]pass_ticket=([^&]+)', url)
        if pass_ticket_match:
            params["pass_ticket"] = urllib.parse.unquote(pass_ticket_match.group(1))
        
        # 提取 uin
        uin_match = re.search(r'[&?]uin=([^&]+)', url)
        if uin_match:
            params["uin"] = urllib.parse.unquote(uin_match.group(1))
        
        # 提取 devicetype
        devicetype_match = re.search(r'[&?]devicetype=([^&]+)', url)
        if devicetype_match:
            params["devicetype"] = urllib.parse.unquote(devicetype_match.group(1))
        
        # 提取 clientversion
        clientversion_match = re.search(r'[&?]clientversion=([^&]+)', url)
        if clientversion_match:
            params["clientversion"] = urllib.parse.unquote(clientversion_match.group(1))
        
        # 提取 __biz
        biz_match = re.search(r'[&?]__biz=([^&]+)', url)
        if biz_match:
            params["biz"] = urllib.parse.unquote(biz_match.group(1))
        
        return params
    
    def deal_request(self, request):
        """处理请求"""
        try:
            url = request.url
            
            if "mp.weixin.qq.com" in url and not self.captured:
                cookie = self._get_cookie(request)
                params = self._extract_params(url)
                
                # 如果提取到了关键参数
                if params.get("key") and params.get("pass_ticket") and cookie:
                    # 更新捕获的参数
                    self.captured_params["cookie"] = cookie
                    self.captured_params["key"] = params.get("key")
                    self.captured_params["pass_ticket"] = params.get("pass_ticket")
                    self.captured_params["uin"] = params.get("uin")
                    self.captured_params["devicetype"] = params.get("devicetype", "UnifiedPCMac")
                    self.captured_params["clientversion"] = params.get("clientversion")
                    
                    if params.get("biz"):
                        self.captured_params["biz"] = params.get("biz")
                    
                    # 保存参数
                    self._save_params()
                    self.captured = True
        
        except Exception as e:
            print(f"❌ 处理请求时出错: {e}")
        
        return request
    
    def deal_response(self, response):
        """处理响应 - 尝试从 HTML 中提取阅读数和点赞数"""
        try:
            url = response.request.url
            
            # 如果是文章页面
            if "mp.weixin.qq.com/s" in url:
                try:
                    text = response.get_text()
                    
                    # 尝试从 HTML 中提取阅读数和点赞数
                    # 新版本可能直接在 HTML 中包含这些数据
                    
                    # 查找 read_num
                    read_num_match = re.search(r'"read_num"\s*:\s*(\d+)', text)
                    if read_num_match:
                        read_num = read_num_match.group(1)
                        print(f"📊 在 HTML 中发现阅读数: {read_num}")
                    
                    # 查找 like_num
                    like_num_match = re.search(r'"like_num"\s*:\s*(\d+)', text)
                    if like_num_match:
                        like_num = like_num_match.group(1)
                        print(f"👍 在 HTML 中发现点赞数: {like_num}")
                    
                    # 查找其他可能的数据格式
                    appmsgstat_match = re.search(r'appmsgstat\s*=\s*({[^}]+})', text)
                    if appmsgstat_match:
                        print(f"📈 在 HTML 中发现统计数据: {appmsgstat_match.group(1)}")
                
                except Exception as e:
                    pass
        
        except Exception as e:
            pass
        
        return response
    
    def _save_params(self):
        """保存参数 - 为每个BIZ创建独立文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        biz = self.captured_params.get("biz", "default")
        
        # 创建BIZ专属目录
        biz_dir = os.path.join(self.params_dir, f"biz_{biz}")
        os.makedirs(biz_dir, exist_ok=True)
        
        # 保存为文本格式（BIZ专属）
        latest_file = os.path.join(biz_dir, "params_latest.txt")
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(f"# 新版本 PC 微信参数\n")
            f.write(f"# BIZ: {biz}\n")
            f.write(f"# 捕获时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"cookie = '{self.captured_params['cookie']}'\n\n")
            f.write(f"key = '{self.captured_params['key']}'\n\n")
            f.write(f"pass_ticket = '{self.captured_params['pass_ticket']}'\n\n")
            f.write(f"uin = '{self.captured_params['uin']}'\n\n")
            f.write(f"devicetype = '{self.captured_params['devicetype']}'\n\n")
            f.write(f"clientversion = '{self.captured_params['clientversion']}'\n")
            f.write(f"\nbiz = '{biz}'\n")
        
        # 保存为 Python 配置（BIZ专属）
        py_file = os.path.join(biz_dir, "config.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(f"# coding: utf-8\n")
            f.write(f"# 新版本 PC 微信参数配置\n")
            f.write(f"# BIZ: {biz}\n")
            f.write(f"# 捕获时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"COOKIE = '{self.captured_params['cookie']}'\n\n")
            f.write(f"KEY = '{self.captured_params['key']}'\n\n")
            f.write(f"PASS_TICKET = '{self.captured_params['pass_ticket']}'\n\n")
            f.write(f"UIN = '{self.captured_params['uin']}'\n\n")
            f.write(f"DEVICETYPE = '{self.captured_params['devicetype']}'\n\n")
            f.write(f"CLIENTVERSION = '{self.captured_params['clientversion']}'\n\n")
            f.write(f"BIZ = '{biz}'\n")
        
        # 保存为 JSON（BIZ专属）
        json_file = os.path.join(biz_dir, "params.json")
        with open(json_file, "w", encoding="utf-8") as f:
            config = {
                "biz": biz,
                "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "params": self.captured_params
            }
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 同时保存到通用位置（兼容旧代码）
        general_py = os.path.join(self.params_dir, "new_wechat_config.py")
        with open(general_py, "w", encoding="utf-8") as f:
            f.write(f"# coding: utf-8\n")
            f.write(f"# 最近捕获的参数 (BIZ: {biz})\n")
            f.write(f"# 捕获时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"COOKIE = '{self.captured_params['cookie']}'\n\n")
            f.write(f"KEY = '{self.captured_params['key']}'\n\n")
            f.write(f"PASS_TICKET = '{self.captured_params['pass_ticket']}'\n\n")
            f.write(f"UIN = '{self.captured_params['uin']}'\n\n")
            f.write(f"DEVICETYPE = '{self.captured_params['devicetype']}'\n\n")
            f.write(f"CLIENTVERSION = '{self.captured_params['clientversion']}'\n\n")
            f.write(f"BIZ = '{biz}'\n")
        
        print(f"\n{'='*80}")
        print(f"🎉 新版本 PC 微信参数已成功捕获！")
        print(f"{'='*80}")
        print(f"📁 BIZ专属保存位置:")
        print(f"   - {py_file}")
        print(f"   - {json_file}")
        print(f"\n📁 通用保存位置:")
        print(f"   - {general_py}")
        print(f"{'='*80}")
        print(f"\n📋 参数预览:")
        print(f"   Cookie (前50字符): {self.captured_params['cookie'][:50]}...")
        print(f"   Key (前50字符): {self.captured_params['key'][:50]}...")
        print(f"   Pass Ticket: {self.captured_params['pass_ticket'][:50]}...")
        print(f"   UIN: {self.captured_params['uin']}")
        print(f"{'='*80}\n")


def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     新版本 PC 微信参数捕获工具                            ║
    ║     New PC WeChat Parameter Capture Tool                  ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    
    🎯 适配新版本 PC 微信
    
    捕获的参数：
       ✓ Cookie          - 身份认证
       ✓ Key             - 认证密钥（替代 appmsg_token）
       ✓ Pass Ticket     - 通行票据
       ✓ UIN             - 用户ID
       ✓ Device Type     - 设备类型
       ✓ Client Version  - 客户端版本
    
    📡 代理服务器：127.0.0.1:8080
    📁 保存目录：params/
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    💡 使用步骤：
       1. 在 PC 微信中打开任意公众号文章
       2. 等待文章加载完成
       3. 参数会自动捕获并保存
    
    ⏳ 等待捕获参数...
    """
    print(banner)


def run(port=8080):
    """启动代理服务器"""
    print_banner()
    
    ca_file = "test/ca.pem"
    cert_file = "test/ca.crt"
    
    if not os.path.exists(ca_file) or not os.path.exists(cert_file):
        print(f"\n❌ 证书文件不存在！")
        return
    
    try:
        proxy = MitmProxy(
            server_addr=("", port),
            RequestHandlerClass=NewPCWeChatProxyHandle,
            bind_and_activate=True,
            https=True,
            ca_file=ca_file,
            cert_file=cert_file,
        )
        
        proxy.register(NewPCWeChatCapture)
        
        print(f"✅ 代理服务器已启动")
        print(f"🔍 监听端口: {port}\n")
        
        proxy.serve_forever()
    
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("⏹️  服务已停止")
        print("💾 所有参数已保存到 params/ 目录")
        print("="*80 + "\n")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")


if __name__ == "__main__":
    run()
