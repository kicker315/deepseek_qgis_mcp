#!/usr/bin/env python3
"""
使用Ollama的deepseek-r1:14b模型与QGIS交互的客户端
"""

import socket
import json
import requests
import sys
import time

class QgisMCPSocketClient:
    """与QGIS MCP插件通信的Socket客户端"""
    
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """连接到QGIS MCP服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"已连接到QGIS MCP服务器 {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"连接QGIS MCP服务器失败: {str(e)}")
            self.socket = None
            return False
    
    def disconnect(self):
        """断开与QGIS MCP服务器的连接"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("已断开与QGIS MCP服务器的连接")
    
    def send_command(self, command_type, params=None):
        """发送命令到QGIS MCP服务器
        
        Args:
            command_type: 命令类型
            params: 命令参数
            
        Returns:
            服务器响应
        """
        if not self.socket:
            if not self.connect():
                return {"status": "error", "message": "未连接到QGIS MCP服务器"}
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            # 发送命令
            command_json = json.dumps(command)
            self.socket.sendall(command_json.encode('utf-8'))
            
            # 接收响应
            response_data = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                try:
                    # 尝试解析JSON，如果成功则表示接收完成
                    json.loads(response_data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    # 数据不完整，继续接收
                    continue
            
            # 解析响应
            response = json.loads(response_data.decode('utf-8'))
            return response
        except Exception as e:
            print(f"发送命令失败: {str(e)}")
            self.disconnect()
            return {"status": "error", "message": str(e)}

class OllamaClient:
    """Ollama API客户端"""
    
    def __init__(self, base_url="http://localhost:11434", model="deepseek-r1:14b"):
        self.base_url = base_url
        self.model = model
        self.api_generate_url = f"{base_url}/api/generate"
    
    def generate(self, prompt, system_prompt=None):
        """向Ollama发送请求并获取生成的回复
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            
        Returns:
            生成的文本响应
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            response = requests.post(self.api_generate_url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"调用Ollama API失败: {str(e)}")
            return f"错误: {str(e)}"

def parse_ai_response_for_qgis_commands(response):
    """解析AI响应，提取QGIS命令
    
    Args:
        response: AI生成的响应文本
        
    Returns:
        解析后的QGIS命令列表
    """
    commands = []
    
    # 简单解析，查找常见的QGIS命令模式
    if "add_vector_layer" in response or "添加矢量图层" in response:
        # 提取路径
        if "D:\\code\\testgdal\\tf.shp" in response:
            commands.append({
                "type": "add_vector_layer",
                "params": {
                    "path": "D:\\code\\testgdal\\tf.shp",
                    "name": "tf"
                }
            })
    
    if "zoom_to_layer" in response or "缩放到图层" in response:
        # 假设最后添加的图层ID会在后续命令中使用
        commands.append({
            "type": "zoom_to_layer",
            "params": {
                "layer_id": "PLACEHOLDER_LAYER_ID"  # 这将在执行时被替换
            }
        })
    
    return commands

def main():
    """主函数"""
    print("Ollama deepseek-r1:14b 与 QGIS 交互示例")
    
    # 初始化客户端
    qgis_client = QgisMCPSocketClient(host='localhost', port=9876)
    ollama_client = OllamaClient(model="deepseek-r1:14b")
    
    # 连接到QGIS
    if not qgis_client.connect():
        print("无法连接到QGIS服务器，请确保QGIS正在运行并且MCP插件已启动")
        return 1
    
    try:
        # 测试QGIS连接
        ping_response = qgis_client.send_command("ping")
        if ping_response.get("status") != "success":
            print(f"QGIS服务器连接测试失败: {ping_response.get('message', '未知错误')}")
            return 1
        
        print("QGIS服务器连接测试成功")
        
        # 示例：使用AI处理自然语言指令
        user_instruction = "加载D:\\code\\testgdal\\tf.shp并缩放到该图层"
        print(f"\n用户指令: {user_instruction}")
        
        # 构建系统提示
        system_prompt = """你是一个GIS专家助手，专门处理QGIS相关任务。
        你需要将用户的自然语言指令转换为QGIS命令。
        可用的QGIS命令包括:
        - add_vector_layer: 添加矢量图层
        - add_raster_layer: 添加栅格图层
        - zoom_to_layer: 缩放到图层
        - get_layers: 获取所有图层
        - remove_layer: 移除图层
        
        请分析用户指令并提供相应的QGIS命令序列。
        """
        
        # 向Ollama发送请求
        print("正在使用Ollama分析指令...")
        ai_response = ollama_client.generate(user_instruction, system_prompt)
        
        print("\nOllama响应:")
        print(ai_response)
        
        # 解析AI响应，提取QGIS命令
        print("\n解析AI响应为QGIS命令...")
        
        # 对于这个特定的例子，我们直接执行已知的命令序列
        # 在实际应用中，可以使用parse_ai_response_for_qgis_commands函数解析AI响应
        
        # 1. 添加矢量图层
        print("\n执行: 添加矢量图层 D:\\code\\testgdal\\tf.shp")
        add_layer_response = qgis_client.send_command("add_vector_layer", {
            "path": "D:\\code\\testgdal\\tf.shp",
            "name": "tf"
        })
        
        if add_layer_response.get("status") != "success":
            print(f"添加图层失败: {add_layer_response.get('message', '未知错误')}")
        else:
            print("添加图层成功")
            layer_id = add_layer_response.get("result", {}).get("id")
            
            # 2. 缩放到图层
            if layer_id:
                print(f"\n执行: 缩放到图层 {layer_id}")
                zoom_response = qgis_client.send_command("zoom_to_layer", {
                    "layer_id": layer_id
                })
                
                if zoom_response.get("status") != "success":
                    print(f"缩放到图层失败: {zoom_response.get('message', '未知错误')}")
                else:
                    print("缩放到图层成功")
        
        print("\n指令执行完成")
        
    except Exception as e:
        print(f"执行过程中出错: {str(e)}")
        return 1
    finally:
        # 断开连接
        qgis_client.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())