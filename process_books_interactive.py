#!/usr/bin/env python3
import os
import requests
import time
import sys
import argparse
from datetime import datetime

# 调试配置
DEBUG_MODE = False
DEBUG_LOG_FILE = "debug_output.txt"

# 预设模型列表
MODEL_LIST = [
    "qwen3.5-9B-nothink-text",
    "text-no-think",
    "qwen3.5-27b-text",
    "qwen3.5:27b",
    "qwen2:7b",
    "qwen2:14b",
    "llama3:70b"
]

# 默认模型
DEFAULT_MODEL = "qwen3.5-9B-nothink-text"

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {'.txt', '.md', '.text'}

# 默认输出目录
DEFAULT_OUTPUT_DIR = "processed_output"


def detect_encoding(file_path):
    """检测文件编码，支持UTF-8和GB2312/GBK"""
    encodings = ['utf-8', 'gb2312', 'gbk', 'gb18030']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue
    
    # 如果都失败，尝试用utf-8并忽略错误
    return 'utf-8'


def read_file(file_path):
    """读取文件内容，自动检测编码"""
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        if DEBUG_MODE:
            print(f"[DEBUG] 文件 {file_path} 使用编码: {encoding}")
        return content
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None


def process_with_ollama(model_name, content):
    """使用Ollama处理内容，每个chunk单独对话"""
    
    wsl_ip = "127.0.0.1"
    
    # 读取系统提示词
    try:
        with open("prompt.txt", 'r', encoding='utf-8') as f:
            system_prompt = f.read()
    except Exception as e:
        print(f"读取提示语文件失败: {e}")
        system_prompt = ""
    
    # 分块处理，每块约4000字符，确保在句子边界处切割
    chunks = []
    chunk_size = 4000
    
    start = 0
    while start < len(content):
        end = start + chunk_size
        
        # 如果不是最后一块，寻找最近的句子结尾
        if end < len(content):
            # 句子结尾标点符号
            sentence_endings = ['。', '！', '？', '……', '；', '：', '"', '"', ''', ''']
            
            # 从end位置向前搜索句子结尾
            found = False
            for i in range(end, start, -1):
                if content[i] in sentence_endings:
                    # 确保标点后面是换行或空格，避免在引号中间切割
                    if i + 1 < len(content) and (content[i + 1] in ['\n', ' ', '\t'] or i + 1 == len(content)):
                        end = i + 1
                        found = True
                        break
            
            # 如果没找到合适的切割点，就按原定大小切割
            if not found:
                end = min(end, len(content))
        else:
            end = len(content)
        
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    
    processed_chunks = []
    
    for i, chunk in enumerate(chunks):
        print(f"处理第 {i+1}/{len(chunks)} 块...")
        
        # 构建单独对话的prompt
        full_prompt = system_prompt + chunk
        
        payload = {
            "model": model_name,
            "prompt": full_prompt,
            "stream": False,
            "think": False,
            "options": {
                "num_predict": 8192,  # 8K token输出限制
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "num_ctx": 8192  # 8K token上下文长度
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
                    assistant_message = result.get('response', chunk)
                    
                    processed_chunks.append(assistant_message)
                    
                    if DEBUG_MODE:
                        with open(DEBUG_LOG_FILE, 'a', encoding='utf-8') as f:
                            f.write(f"\n=== 块 {i+1} 输出 ===\n")
                            f.write(assistant_message)
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
    
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='文本处理系统 - 使用Ollama模型润色文本')
    parser.add_argument('input_path', nargs='?', help='输入文件或目录路径')
    parser.add_argument('-m', '--model', choices=MODEL_LIST, default=DEFAULT_MODEL,
                        help=f'选择使用的模型 (默认: {DEFAULT_MODEL})')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT_DIR,
                        help=f'输出目录路径 (默认: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='启用调试模式')
    parser.add_argument('--list-models', action='store_true',
                        help='列出所有可用模型')
    
    args = parser.parse_args()
    
    # 列出模型并退出
    if args.list_models:
        print("可用模型列表:")
        for i, model in enumerate(MODEL_LIST, 1):
            default_mark = " [默认]" if model == DEFAULT_MODEL else ""
            print(f"{i}. {model}{default_mark}")
        return
    
    # 设置调试模式
    DEBUG_MODE = args.debug
    if DEBUG_MODE:
        print("\n[DEBUG] 调试模式已开启")
        if os.path.exists(DEBUG_LOG_FILE):
            os.remove(DEBUG_LOG_FILE)
    
    print("=" * 60)
    print("文本处理系统")
    print("=" * 60)
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 设置模型
    selected_model = args.model
    print(f"使用模型: {selected_model}")
    
    # 设置输入路径
    if args.input_path:
        input_path = args.input_path
    else:
        print("\n错误: 请提供输入文件或目录路径")
        print(f"用法: python {sys.argv[0]} <输入路径> [选项]")
        print(f"帮助: python {sys.argv[0]} --help")
        return
    
    if not os.path.exists(input_path):
        print(f"输入路径不存在: {input_path}")
        return
    
    # 设置输出目录
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    # 判断是文件还是目录
    if os.path.isfile(input_path):
        # 单个文件
        if not is_supported_file(input_path):
            print(f"不支持的文件格式: {input_path}")
            print(f"支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}")
            return
        
        with open("text_processing.log", 'a', encoding='utf-8') as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始新的处理会话\n")
            f.write(f"输入文件: {input_path}\n")
            f.write(f"输出目录: {output_dir}\n")
            f.write(f"模型: {selected_model}\n")
            f.write(f"{'=' * 60}\n")
        
        success = process_single_file(input_path, output_dir, selected_model)
        
        print(f"\n{'=' * 60}")
        print(f"处理完成!")
        print(f"结果: {'成功' if success else '失败'}")
        print(f"输出目录: {os.path.abspath(output_dir)}")
        print(f"{'=' * 60}")
        
        with open("text_processing.log", 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 会话结束: {'成功' if success else '失败'}\n")
    
    else:
        # 目录
        with open("text_processing.log", 'a', encoding='utf-8') as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始新的处理会话\n")
            f.write(f"输入目录: {input_path}\n")
            f.write(f"输出目录: {output_dir}\n")
            f.write(f"模型: {selected_model}\n")
            f.write(f"{'=' * 60}\n")
        
        print(f"\n正在扫描目录: {input_path}")
        all_files = find_all_files(input_path)
        
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
        print("\n[DEBUG] 调试日志已保存到:", DEBUG_LOG_FILE)


if __name__ == "__main__":
    main()
