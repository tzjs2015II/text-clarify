#!/usr/bin/env python3
import os
import requests
import time
import sys
from datetime import datetime

# 调试配置
DEBUG_MODE = False
DEBUG_LOG_FILE = "debug_output.txt"

# 预设模型列表
MODEL_LIST = [
    "qwen3.5-27b-text",
    "qwen3.5:27b",
    "qwen2:7b",
    "qwen2:14b",
    "llama3:70b"
]

# 默认模型
DEFAULT_MODEL = "qwen3.5-27b-text"

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {'.txt', '.md', '.text'}

# 默认输入和输出目录
DEFAULT_INPUT_DIR = "testFile"
DEFAULT_OUTPUT_DIR = "processed_output"


def select_model():
    """选择模型"""
    print("=" * 60)
    print("模型选择")
    print("=" * 60)
    
    print(f"\n请选择要使用的模型 (直接回车使用默认: {DEFAULT_MODEL}):")
    for i, option in enumerate(MODEL_LIST, 1):
        default_mark = " [默认]" if option == DEFAULT_MODEL else ""
        print(f"{i}. {option}{default_mark}")
    
    while True:
        try:
            user_input = input("请输入选择的序号: ").strip()
            if user_input == "":
                return DEFAULT_MODEL
            choice = int(user_input)
            if 1 <= choice <= len(MODEL_LIST):
                return MODEL_LIST[choice-1]
            else:
                print(f"请输入1到{len(MODEL_LIST)}之间的数字")
        except ValueError:
            print("请输入有效的数字")


def read_file(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None


def process_with_ollama(model_name, content):
    """使用Ollama处理内容"""
    
    wsl_ip = "127.0.0.1"
    
    chunks = []
    chunk_size = 4000
    for i in range(0, len(content), chunk_size):
        chunks.append(content[i:i+chunk_size])
    
    processed_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"处理第 {i+1}/{len(chunks)} 块...")
        
        try:
            with open("prompt.txt", 'r', encoding='utf-8') as f:
                prompt = f.read()
        except Exception as e:
            print(f"读取提示语文件失败: {e}")
            prompt = ""
        
        full_prompt = prompt + chunk
        
        payload = {
            "model": model_name,
            "prompt": full_prompt,
            "stream": False,
            "think": False,
            "options": {
                "num_predict": 8192,
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        max_retries = 1
        retry_delay = 10
        success = False
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"http://{wsl_ip}:11434/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    processed_chunks.append(result.get('response', chunk))
                    
                    if DEBUG_MODE:
                        with open(DEBUG_LOG_FILE, 'a', encoding='utf-8') as f:
                            f.write(f"\n=== 块 {i+1} 输出 ===\n")
                            f.write(result.get('response', chunk))
                            f.write("\n=================\n")
                    
                    success = True
                    break
                else:
                    print(f"Ollama API 错误: {response.status_code}")
                    print(f"尝试 {attempt+1}/{max_retries} 失败，{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
            except Exception as e:
                print(f"调用Ollama失败: {e}")
                print(f"尝试 {attempt+1}/{max_retries} 失败，{retry_delay}秒后重试...")
                time.sleep(retry_delay)
        
        if not success:
            error_msg = f"所有 {max_retries} 次尝试均失败，保留原始内容"
            print(error_msg)
            with open("text_processing.log", 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg} (模型: {model_name}, 块号: {i+1})\n")
            processed_chunks.append(chunk)
    
    return '\n'.join(processed_chunks)


def write_file(file_path, content):
    """写入文件"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"文件已保存到: {file_path}")
        return True
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False


def is_supported_file(file_path):
    """检查文件是否为支持的格式"""
    _, ext = os.path.splitext(file_path)
    return ext.lower() in SUPPORTED_EXTENSIONS


def find_all_files(input_dir):
    """递归查找所有支持的文件"""
    all_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if is_supported_file(file_path):
                all_files.append(file_path)
    return sorted(all_files)


def process_single_file(input_file, output_dir, model_name):
    """处理单个文件"""
    print(f"\n{'=' * 60}")
    print(f"处理文件: {input_file}")
    print(f"{'=' * 60}")
    
    content = read_file(input_file)
    if not content:
        print(f"无法读取文件: {input_file}")
        return False
    
    print(f"原始文件大小: {len(content)} 字符")
    
    processed_content = process_with_ollama(model_name, content)
    
    filename = os.path.basename(input_file)
    output_file = os.path.join(output_dir, filename)
    
    write_file(output_file, processed_content)
    
    print(f"处理后文件大小: {len(processed_content)} 字符")
    
    with open("text_processing.log", 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 处理完成: {input_file} -> {output_file}\n")
    
    return True


def main():
    global DEBUG_MODE
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--debug" or sys.argv[1] == "-d":
            DEBUG_MODE = True
            print("\n[DEBUG] 调试模式已开启")
            if os.path.exists(DEBUG_LOG_FILE):
                os.remove(DEBUG_LOG_FILE)
        elif sys.argv[1] == "--no-debug" or sys.argv[1] == "-nd":
            DEBUG_MODE = False
            print("\n[DEBUG] 调试模式已关闭")
    
    print("=" * 60)
    print("文本处理系统")
    print("=" * 60)
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    selected_model = select_model()
    print(f"\n你选择了模型: {selected_model}")
    
    input_dir = input(f"\n请输入输入目录路径 (直接回车使用默认: {DEFAULT_INPUT_DIR}): ").strip()
    if not input_dir:
        input_dir = DEFAULT_INPUT_DIR
    
    if not os.path.exists(input_dir):
        print(f"输入目录不存在: {input_dir}")
        return
    
    output_dir = input(f"请输入输出目录路径 (直接回车使用默认: {DEFAULT_OUTPUT_DIR}): ").strip()
    if not output_dir:
        output_dir = DEFAULT_OUTPUT_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    with open("text_processing.log", 'a', encoding='utf-8') as f:
        f.write(f"\n{'=' * 60}\n")
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始新的处理会话\n")
        f.write(f"输入目录: {input_dir}\n")
        f.write(f"输出目录: {output_dir}\n")
        f.write(f"模型: {selected_model}\n")
        f.write(f"{'=' * 60}\n")
    
    print(f"\n正在扫描目录: {input_dir}")
    all_files = find_all_files(input_dir)
    
    if not all_files:
        print(f"在目录中没有找到支持的文件。支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}")
        return
    
    print(f"找到 {len(all_files)} 个文件")
    
    success_count = 0
    for i, input_file in enumerate(all_files, 1):
        print(f"\n[{i}/{len(all_files)}]")
        if process_single_file(input_file, output_dir, selected_model):
            success_count += 1
    
    print(f"\n{'=' * 60}")
    print(f"处理完成!")
    print(f"成功: {success_count}/{len(all_files)}")
    print(f"输出目录: {os.path.abspath(output_dir)}")
    print(f"{'=' * 60}")
    
    with open("text_processing.log", 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 会话结束: 成功 {success_count}/{len(all_files)}\n")
    
    if DEBUG_MODE and os.path.exists(DEBUG_LOG_FILE):
        print("\n[DEBUG] 清理调试日志文件")
        os.remove(DEBUG_LOG_FILE)


if __name__ == "__main__":
    main()
