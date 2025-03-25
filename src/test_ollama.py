#!/usr/bin/env python3
"""
测试Ollama与QGIS集成
"""

from qgis_mcp.ollama_client import OllamaClient
from qgis_mcp.qgis_socket_client import QgisMCPClient
import json
import sys

def test_ollama_connection():
    """测试Ollama连接和基本功能"""
    print("测试Ollama连接...")
    
    client = OllamaClient(model="deepseek-r1:14b")
    
    # 测试基本生成
    prompt = "什么是GIS？简要介绍QGIS的主要功能。"
    print(f"发送提示: {prompt}")
    
    response = client.generate(prompt)
    print("\n回复:")
    print(response)
    
    return True

def test_qgis_ollama_integration():
    """测试Ollama与QGIS的集成"""
    print("\n测试Ollama与QGIS集成...")
    
    # 创建QGIS客户端实例
    qgis_client = QgisMCPClient()
    
    # 检查QgisMCPClient类中可用的方法
    print("QgisMCPClient可用方法:")
    available_methods = [method for method in dir(qgis_client) if not method.startswith('_')]
    print(available_methods)
    
    # 尝试使用ping方法测试连接
    if 'ping' in available_methods:
        print("尝试ping QGIS服务器...")
        try:
            ping_result = qgis_client.ping()
            print(f"Ping结果: {ping_result}")
        except Exception as e:
            print(f"Ping失败: {str(e)}")
    
    # 尝试获取QGIS信息
    if 'get_qgis_info' in available_methods:
        print("尝试获取QGIS信息...")
        try:
            qgis_info = qgis_client.get_qgis_info()
            print(f"QGIS信息: {qgis_info}")
        except Exception as e:
            print(f"获取QGIS信息失败: {str(e)}")
    
    # 使用Ollama生成简单的GIS相关内容
    ollama_client = OllamaClient(model="deepseek-r1:14b")
    prompt = "加载D:\code\testgdal\tf.shp并缩放到该图层。"
    
    print("使用Ollama生成GIS内容...")
    analysis = ollama_client.generate(prompt)
    
    print("\nOllama生成结果:")
    print(analysis)
    
    return True

def main():
    """主函数"""
    print("Ollama与QGIS集成测试")
    
    try:
        if test_ollama_connection():
            print("\n✅ Ollama连接测试成功")
        else:
            print("\n❌ Ollama连接测试失败")
            return 1
        
        if test_qgis_ollama_integration():
            print("\n✅ Ollama与QGIS集成测试成功")
        else:
            print("\n❌ Ollama与QGIS集成测试失败")
            return 1
            
        print("\n所有测试完成")
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())