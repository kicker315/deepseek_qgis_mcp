import requests
import json
import logging

logger = logging.getLogger("OllamaClient")

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="deepseek-r1:14b"):
        """初始化Ollama客户端
        
        Args:
            base_url: Ollama API的基础URL
            model: 要使用的模型名称
        """
        self.base_url = base_url
        self.model = model
        self.api_generate_url = f"{base_url}/api/generate"
        
    def generate(self, prompt, system_prompt=None, stream=False):
        """向Ollama发送请求并获取生成的回复
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            stream: 是否使用流式响应
            
        Returns:
            生成的文本响应
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            response = requests.post(self.api_generate_url, json=payload)
            response.raise_for_status()
            
            if stream:
                # 处理流式响应
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        full_response += chunk.get("response", "")
                        if chunk.get("done", False):
                            break
                return full_response
            else:
                # 处理普通响应
                return response.json().get("response", "")
                
        except Exception as e:
            logger.error(f"Error calling Ollama API: {str(e)}")
            return f"Error: {str(e)}"
            
    def process_qgis_command(self, qgis_data, system_prompt=None):
        """处理QGIS数据并通过Ollama生成响应
        
        Args:
            qgis_data: QGIS相关数据（通常是JSON格式的字符串）
            system_prompt: 可选的系统提示
            
        Returns:
            Ollama生成的响应
        """
        prompt = f"以下是QGIS的数据，请分析并提供相关建议或执行相应操作：\n\n{qgis_data}"
        
        if not system_prompt:
            system_prompt = """你是一个GIS专家助手，专门处理QGIS相关任务。
            分析用户提供的GIS数据，提供专业的建议，并根据需要生成可执行的QGIS命令。
            保持回答简洁、专业，并确保命令的准确性。"""
            
        return self.generate(prompt, system_prompt)