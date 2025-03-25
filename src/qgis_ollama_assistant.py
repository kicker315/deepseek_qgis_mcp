#!/usr/bin/env python3
"""
QGIS Ollama助手 - 使用deepseek-r1:14b模型与QGIS交互
"""

import socket
import json
import requests
import sys
import re
import time
from typing import List, Dict, Any, Optional, Tuple
# from .ollama_client import OllamaClient
from qgis_mcp.ollama_client import OllamaClient

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

class QgisOllamaAssistant:
    """QGIS deepseek助手 - 使用deepseek-r1:14b模型与QGIS交互"""
    
    def __init__(self, qgis_host='localhost', qgis_port=9876, 
                 ollama_url="http://localhost:11434", ollama_model="deepseek-r1:14b"):
        self.qgis_client = QgisMCPSocketClient(host=qgis_host, port=qgis_port)
        self.ollama_client = OllamaClient(base_url=ollama_url, model=ollama_model)
        self.context = {
            "last_command": None,
            "last_layer_id": None,
            "project_info": None,
            "layers": []
        }
        self.system_prompt = """你是一个GIS专家助手，专门处理QGIS相关任务。
        你需要将用户的自然语言指令转换为QGIS命令。
        可用的QGIS命令包括:
        - add_vector_layer: 添加矢量图层，参数包括path(文件路径)和name(图层名称)
        - add_raster_layer: 添加栅格图层，参数包括path(文件路径)和name(图层名称)
        - zoom_to_layer: 缩放到图层，参数包括layer_id(图层ID)
        - get_layers: 获取所有图层
        - remove_layer: 移除图层，参数包括layer_id(图层ID)
        - get_project_info: 获取项目信息
        - execute_processing: 执行处理算法，参数包括algorithm(算法名称)和parameters(算法参数)
        
        常用的处理算法包括:
        - native:randompointsinextent: 在范围内生成随机点，参数包括:
          * EXTENT: 范围，格式为"xmin,xmax,ymin,ymax"
          * POINTS_NUMBER: 点的数量
          * OUTPUT: 输出文件路径
        - native:buffer: 创建缓冲区，参数包括:
          * INPUT: 输入图层ID
          * DISTANCE: 缓冲距离
          * OUTPUT: 输出文件路径
        
        请分析用户指令并提供相应的QGIS命令序列，格式为JSON。例如:
        [
            {"command": "add_vector_layer", "params": {"path": "D:/data/roads.shp", "name": "roads"}},
            {"command": "zoom_to_layer", "params": {"layer_id": "roads_123456"}}
        ]
        
        注意：确保使用正确的算法名称和参数格式。
        """
    
    def get_supported_commands(self) -> List[str]:
        """获取服务器支持的命令列表"""
        response = self.qgis_client.send_command("get_commands")
        if response.get("status") == "success":
            return response.get("result", [])
        return []
    
    def connect(self) -> bool:
        """连接到QGIS服务器"""
        if self.qgis_client.connect():
            # 尝试获取支持的命令
            commands = self.get_supported_commands()
            if commands:
                print("服务器支持的命令:")
                for cmd in commands:
                    print(f"  - {cmd}")
            return True
        return False
        
    def disconnect(self) -> None:
        """断开与QGIS服务器的连接"""
        self.qgis_client.disconnect()
    
    def update_context(self) -> None:
        """更新上下文信息"""
        # 获取项目信息
        project_info = self.qgis_client.send_command("get_project_info")
        if project_info.get("status") == "success":
            self.context["project_info"] = project_info.get("result")
        
        # 获取图层列表
        layers = self.qgis_client.send_command("get_layers")
        if layers.get("status") == "success":
            self.context["layers"] = layers.get("result")
    
    def parse_ai_response(self, response: str) -> List[Dict[str, Any]]:
        """解析AI响应，提取QGIS命令
        
        Args:
            response: AI生成的响应文本
            
        Returns:
            解析后的QGIS命令列表
        """
        commands = []
        
        # 尝试从响应中提取JSON格式的命令
        json_pattern = r'\[\s*{.*}\s*\]'
        json_matches = re.findall(json_pattern, response, re.DOTALL)
        
        if json_matches:
            try:
                commands = json.loads(json_matches[0])
                return commands
            except json.JSONDecodeError:
                pass
        
        # 如果无法提取JSON，尝试通过关键词识别命令
        if "add_vector_layer" in response or "添加矢量图层" in response:
            # 尝试提取文件路径
            path_pattern = r'["\']([D|d]:\\[^"\']+\.shp)["\']'
            path_matches = re.findall(path_pattern, response)
            
            if path_matches:
                path = path_matches[0]
                name = path.split('\\')[-1].split('.')[0]
                commands.append({
                    "command": "add_vector_layer",
                    "params": {
                        "path": path,
                        "name": name
                    }
                })
        
        if "zoom_to_layer" in response or "缩放到图层" in response:
            # 如果前面有添加图层的命令，则缩放到该图层
            if commands and commands[-1]["command"] == "add_vector_layer":
                commands.append({
                    "command": "zoom_to_layer",
                    "params": {
                        "layer_id": "PLACEHOLDER_LAYER_ID"  # 这将在执行时被替换
                    }
                })
        
        return commands
    
    def execute_commands(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行QGIS命令序列
        
        Args:
            commands: 要执行的命令列表
            
        Returns:
            命令执行结果列表
        """
        results = []
        
        for cmd in commands:
            command_type = cmd.get("command")
            params = cmd.get("params", {})
            
            # 特殊处理：如果是zoom_to_layer命令且layer_id是占位符
            if command_type == "zoom_to_layer" and params.get("layer_id") == "PLACEHOLDER_LAYER_ID":
                if self.context["last_layer_id"]:
                    params["layer_id"] = self.context["last_layer_id"]
                else:
                    print("警告: 没有可用的图层ID，跳过缩放命令")
                    continue
            
            # 特殊处理：execute_processing命令
            if command_type == "execute_processing":
                # 检查算法名称
                algorithm = params.get("algorithm", "")
                
                # 修正算法名称
                if algorithm == "qgis:generate_random_points":
                    params["algorithm"] = "native:randompointsinextent"
                    print(f"修正算法名称: 'qgis:generate_random_points' -> 'native:randompointsinextent'")
                
                # 检查参数格式
                if "parameters" in params:
                    # 对于随机点生成，确保参数正确
                    if "native:randompointsinextent" in params["algorithm"]:
                        # 确保参数符合QGIS要求
                        if "OUTPUT_FILE" in params["parameters"]:
                            # 将OUTPUT_FILE转换为OUTPUT
                            output_file = params["parameters"].pop("OUTPUT_FILE")
                            params["parameters"]["OUTPUT"] = output_file
                            print(f"修正参数: 'OUTPUT_FILE' -> 'OUTPUT'")
                        
                        # 添加必要的EXTENT参数
                        if "EXTENT" not in params["parameters"]:
                            # 获取当前地图范围
                            extent_response = self.qgis_client.send_command("get_map_extent")
                            if extent_response.get("status") == "success":
                                extent = extent_response.get("result", {}).get("extent")
                                if extent:
                                    params["parameters"]["EXTENT"] = extent
                                    print(f"添加缺失参数: 'EXTENT' = {extent}")
                                else:
                                    # 使用默认范围
                                    params["parameters"]["EXTENT"] = "0,1,0,1"
                                    print("添加默认EXTENT参数: '0,1,0,1'")
                            else:
                                # 使用默认范围
                                params["parameters"]["EXTENT"] = "0,1,0,1"
                                print("添加默认EXTENT参数: '0,1,0,1'")
            
            # 检查文件路径是否存在
            if command_type == "add_vector_layer" or command_type == "add_raster_layer":
                import os
                path = params.get("path", "")
                if not os.path.exists(path):
                    print(f"警告: 文件不存在: {path}")
                    # 检查是否有前一个命令生成了该文件
                    if len(results) > 0 and results[-1]["command"] == "execute_processing":
                        prev_result = results[-1]["response"]
                        if prev_result.get("status") != "success":
                            print(f"跳过添加图层命令，因为前一个处理命令失败")
                            continue
            
            print(f"执行命令: {command_type}, 参数: {params}")
            response = self.qgis_client.send_command(command_type, params)
            
            # 保存结果
            results.append({
                "command": command_type,
                "params": params,
                "response": response
            })
            
            # 如果命令执行失败，打印详细错误信息
            if response.get("status") != "success":
                error_msg = response.get("message", "未知错误")
                print(f"命令执行失败: {error_msg}")
            
            # 更新上下文
            if command_type == "add_vector_layer" or command_type == "add_raster_layer":
                if response.get("status") == "success":
                    self.context["last_layer_id"] = response.get("result", {}).get("id")
            
            self.context["last_command"] = command_type
        
        # 执行完所有命令后更新上下文
        self.update_context()
        
        return results
    
    def process_instruction(self, instruction: str) -> Dict[str, Any]:
        """处理用户指令
        
        Args:
            instruction: 用户自然语言指令
            
        Returns:
            处理结果
        """
        # 更新上下文
        self.update_context()
        
        # 构建提示
        context_json = json.dumps(self.context, ensure_ascii=False, indent=2)
        prompt = f"""用户指令: {instruction}

当前QGIS上下文:
{context_json}

请分析用户指令，并提供相应的QGIS命令序列。"""
        
        # 使用Ollama生成响应
        print("正在使用deepseek分析指令...")
        ai_response = self.ollama_client.generate(prompt, self.system_prompt)
        
        print("\ndeepseek响应:")
        print(ai_response)
        
        # 解析AI响应
        print("\n解析AI响应为QGIS命令...")
        commands = self.parse_ai_response(ai_response)
        
        if not commands:
            print("未能从AI响应中提取有效的QGIS命令")
            # 对于特定指令，提供默认命令
            if "加载" in instruction and "tf.shp" in instruction and "缩放" in instruction:
                commands = [
                    {
                        "command": "add_vector_layer",
                        "params": {
                            "path": "D:\\code\\testgdal\\tf.shp",
                            "name": "tf"
                        }
                    },
                    {
                        "command": "zoom_to_layer",
                        "params": {
                            "layer_id": "PLACEHOLDER_LAYER_ID"
                        }
                    }
                ]
                print("使用默认命令序列")
        
        # 执行命令
        results = self.execute_commands(commands)
        
        return {
            "instruction": instruction,
            "ai_response": ai_response,
            "commands": commands,
            "results": results
        }

def main():
    """主函数"""
    print("QGIS deepseek助手 - 使用deepseek-r1:14b模型与QGIS交互")
    
    # 创建助手实例
    assistant = QgisOllamaAssistant()
    
    # 连接到QGIS
    if not assistant.connect():
        print("无法连接到QGIS服务器，请确保QGIS正在运行并且MCP插件已启动")
        return 1
    
    try:
        # 示例：处理特定指令
        instruction = "加载D:\\code\\testgdal\\tf.shp并缩放到该图层"
        # instruction = "新建工程,保存到D:\\code\\testgdal"

        print(f"\n处理用户指令: {instruction}")
        
        result = assistant.process_instruction(instruction)
        
        # 显示执行结果摘要
        print("\n执行结果摘要:")
        for cmd_result in result["results"]:
            status = cmd_result["response"].get("status", "unknown")
            command = cmd_result["command"]
            status_emoji = "✅" if status == "success" else "❌"
            print(f"{status_emoji} {command}: {status}")
        
        # 交互式模式
        print("\n进入交互模式，输入'exit'退出")
        while True:
            user_input = input("\n请输入QGIS指令: ")
            if user_input.lower() in ["exit", "quit", "退出"]:
                break
            
            result = assistant.process_instruction(user_input)
            
            # 显示执行结果摘要
            print("\n执行结果摘要:")
            for cmd_result in result["results"]:
                status = cmd_result["response"].get("status", "unknown")
                command = cmd_result["command"]
                status_emoji = "✅" if status == "success" else "❌"
                print(f"{status_emoji} {command}: {status}")
    
    except Exception as e:
        print(f"执行过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # 断开连接
        assistant.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())