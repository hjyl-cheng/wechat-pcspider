# coding: utf-8
"""
参数捕获进程包装器 - 支持双向通信
"""
import os
import sys
import time
from multiprocessing import Queue
# 全局变量，用于在回调中访问queue
_result_queue = None
def run_capture_process(command_queue, result_queue):
    """
    在独立进程中运行参数捕获
    
    Parameters
    ----------
    command_queue : Queue
        接收命令的队列（父 -> 子）
    result_queue : Queue
        发送结果的队列（子 -> 父）
    """
    global _result_queue
    _result_queue = result_queue
    
    try:
        # 发送启动消息
        result_queue.put({
            'type': 'status',
            'status': 'starting',
            'message': '代理服务器启动中...'
        })
        
        # 导入捕获模块
        from capture_new_wechat import NewPCWeChatProxyHandle, NewPCWeChatCapture
        from wechatarticles.proxy import MitmProxy
        
        # 创建代理
        result_queue.put({
            'type': 'status',
            'status': 'initializing',
            'message': '初始化代理服务器...'
        })
        
        # 检查证书文件
        ca_file = "test/ca.pem"
        cert_file = "test/ca.crt"
        
        if not os.path.exists(ca_file) or not os.path.exists(cert_file):
            result_queue.put({
                'type': 'error',
                'status': 'error',
                'message': f'证书文件不存在: {ca_file} 或 {cert_file}'
            })
            return
        
        # 创建带通知功能的捕获类
        class NotifyingCapture(NewPCWeChatCapture):
            """添加Queue通知和数据库保存的捕获类"""
            
            def _save_params(self):
                """保存参数并通过Queue通知，同时保存到数据库"""
                global _result_queue
                try:
                    # 调用父类保存方法（保存到文件）
                    super()._save_params()
                    
                    # 额外保存到数据库
                    biz = self.captured_params.get('biz', 'unknown')
                    
                    if _result_queue:
                        _result_queue.put({
                            'type': 'status',
                            'status': 'saving_to_db',
                            'message': f'正在保存参数到数据库 (BIZ: {biz})...'
                        })
                    
                    if biz != 'unknown':
                        try:
                            # 在子进程中重新导入
                            import sys
                            import os
                            
                            # 确保父目录在 sys.path 中
                            current_dir = os.path.dirname(os.path.abspath(__file__))
                            if current_dir not in sys.path:
                                sys.path.insert(0, current_dir)
                            
                            from db_operations import save_parameters
                            
                            params_dict = {
                                'cookie': self.captured_params.get('cookie', ''),
                                'key': self.captured_params.get('key', ''),
                                'pass_ticket': self.captured_params.get('pass_ticket', ''),
                                'uin': self.captured_params.get('uin', '')
                            }
                            
                            # 执行保存
                            result = save_parameters(biz, params_dict)
                            
                            if _result_queue:
                                _result_queue.put({
                                    'type': 'status',
                                    'status': 'db_saved',
                                    'message': f'✅ 参数已保存到数据库 (ID: {result.get("id")})'
                                })
                        except Exception as db_error:
                            import traceback
                            error_trace = traceback.format_exc()
                            
                            if _result_queue:
                                _result_queue.put({
                                    'type': 'warning',
                                    'status': 'db_save_failed',
                                    'message': f'⚠️ 数据库保存失败: {str(db_error)}',
                                    'traceback': error_trace
                                })
                    
                    # 发送成功消息
                    if _result_queue:
                        _result_queue.put({
                            'type': 'complete',
                            'status': 'success',
                            'message': '参数捕获成功！',
                            'biz': biz,
                            'params': {
                                'cookie_length': len(self.captured_params.get('cookie', '') or ''),
                                'has_key': bool(self.captured_params.get('key')),
                                'has_pass_ticket': bool(self.captured_params.get('pass_ticket')),
                            }
                        })
                except Exception as e:
                    import traceback
                    if _result_queue:
                        _result_queue.put({
                            'type': 'error',
                            'status': 'error',
                            'message': f'保存参数失败: {str(e)}',
                            'traceback': traceback.format_exc()
                        })

        
        # 按照 capture_new_wechat.py 的方式创建代理
        port = 8888
        proxy = MitmProxy(
            server_addr=("", port),
            RequestHandlerClass=NewPCWeChatProxyHandle,
            bind_and_activate=True,
            https=True,
            ca_file=ca_file,
            cert_file=cert_file,
        )
        
        # 注册带通知功能的捕获器
        proxy.register(NotifyingCapture)
        
        result_queue.put({
            'type': 'status',
            'status': 'listening',
            'message': f'代理服务器已启动，监听端口 {port}'
        })
        
        # 启动代理（会一直运行直到捕获完成）
        result_queue.put({
            'type': 'status',
            'status': 'capturing',
            'message': '等待微信请求...'
        })
        
        # 运行代理
        proxy.serve_forever()
        
    except KeyboardInterrupt:
        result_queue.put({
            'type': 'interrupted',
            'status': 'interrupted',
            'message': '捕获被中断'
        })
    except Exception as e:
        import traceback
        result_queue.put({
            'type': 'error',
            'status': 'error',
            'message': f'捕获失败: {str(e)}',
            'traceback': traceback.format_exc()
        })

