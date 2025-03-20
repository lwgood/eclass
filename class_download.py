import json
import subprocess
import os
import time
import re
import logging
from tqdm import tqdm

def load_config():
    """
    加载配置文件
    :return: 配置字典
    """
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载配置文件时发生异常: {e}")
        raise

def setup_logging(output_dir):
    """
    配置日志记录
    :param output_dir: 日志文件保存目录
    """
    log_file = os.path.join(output_dir, "download.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file)  # 日志保存到 output_dir 目录
        ]
    )

def read_json_file(file_path):
    """
    读取原始 JSON 文件
    :param file_path: JSON 文件路径
    :return: JSON 数据
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def process_data(original_data):
    """
    处理数据，提取需要的字段
    :param original_data: 原始 JSON 数据
    :return: 处理后的数据
    """
    result = []
    for item in original_data:
        class_name = item["level_name"]
        level_names = [child["level_name"] for child in item.get("child", [])]
        result.append({
            "class_name": class_name,
            "level_name": level_names
        })
    return result

def get_duration(m3u8_url):
    """
    获取视频总时长（秒）
    :param m3u8_url: m3u8 视频地址
    :return: 视频总时长（秒），如果无法获取则返回 None
    """
    try:
        cmd = [
            "ffmpeg",
            "-i", m3u8_url,
            "-hide_banner"
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
        if duration_match:
            hours, minutes, seconds = map(float, duration_match.groups())
            return hours * 3600 + minutes * 60 + seconds
        logging.warning(f"无法获取 {m3u8_url} 的时长")  # 写入日志文件
        return None
    except Exception as e:
        logging.error(f"获取时长时发生异常: {e}")       # 写入日志文件
        return None

def download_video(m3u8_url, output_file, current_index, total_videos, timeout):
    """
    使用 ffmpeg 下载单个 m3u8 视频并显示进度条，支持卡住跳过
    :param m3u8_url: m3u8 视频地址
    :param output_file: 输出文件路径
    :param current_index: 当前下载的视频序号
    :param total_videos: 总视频数
    :param timeout: 卡住判断时间（秒）
    """
    try:
        # 获取视频总时长
        total_duration = get_duration(m3u8_url)
        if total_duration is None:
            logging.warning(f"无法获取 {m3u8_url} 的时长，使用默认进度条")  # 写入日志文件
            total_duration = 0

        # 输出开始下载信息
        logging.info(f"开始下载: {m3u8_url} -> {output_file}")  # 写入日志文件
        tqdm.write(f"正在下载第 {current_index} 个视频: {os.path.basename(output_file)}")

        # ffmpeg 下载命令
        cmd = [
            "ffmpeg",
            "-i", m3u8_url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-progress", "pipe:1",  # 输出进度信息到管道
            "-y",  # 覆盖已有文件
            output_file
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # 使用 tqdm 显示进度条
        with tqdm(
            total=100,  # 以百分比为基准
            desc="下载进度",
            bar_format="{l_bar}{bar:10}| {percentage:3.0f}%",
            position=0,  # 固定进度条位置
            leave=False  # 下载完成后不保留进度条
        ) as pbar:
            last_progress = 0  # 上一次的进度百分比
            last_update_time = time.time()  # 上一次进度更新时间

            while process.poll() is None:
                line = process.stdout.readline()
                if "out_time=" in line:
                    time_match = re.search(r"out_time=(\d+):(\d+):(\d+\.\d+)", line)
                    if time_match:
                        hours, minutes, seconds = map(float, time_match.groups())
                        current_time = hours * 3600 + minutes * 60 + seconds
                        if total_duration > 0:
                            # 计算百分比
                            progress = (current_time / total_duration) * 100
                            pbar.n = min(progress, 100)
                            pbar.refresh()

                            # 检查是否卡住
                            if progress == last_progress:
                                if time.time() - last_update_time > timeout:
                                    process.terminate()
                                    logging.warning(f"下载卡住，跳过视频: {m3u8_url}")  # 写入日志文件
                                    tqdm.write(f"下载卡住，跳过视频: {m3u8_url}")
                                    return False
                            else:
                                last_progress = progress
                                last_update_time = time.time()
                        else:
                            pbar.update(1)

                # 将 ffmpeg 的 stderr 输出写入日志文件，并添加时间戳
                stderr_line = process.stderr.readline()
                if stderr_line.strip():  # 忽略空行
                    logging.info(stderr_line.strip())  # 使用 logging 格式化时间戳

            # 检查下载是否成功
            process.wait()
            if process.returncode == 0:
                logging.info(f"下载成功: {output_file}")  # 写入日志文件
                tqdm.write(f"下载完成! 视频保存路径：{output_file} ✅")
                return True
            else:
                error_msg = process.stderr.read()
                logging.error(f"下载失败: {output_file}\n错误信息: {error_msg}")  # 写入日志文件
                tqdm.write(f"下载失败: {output_file}\n错误信息: {error_msg}")
                return False

    except Exception as e:
        logging.error(f"下载视频时发生异常: {e}")  # 写入日志文件
        tqdm.write(f"下载视频时发生异常: {e}")
        return False

def main():
    """
    主函数：读取 m3u8 地址列表并下载视频
    """
    # 加载配置文件
    config = load_config()
    class_url = config["class_url"]
    output_dir = config["output_dir"]
    class_name = config["class_name"]
    timeout = config["timeout"]

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 配置日志记录
    setup_logging(output_dir)

    # 读取并处理原始 JSON 文件
    original_data = read_json_file(class_name)
    data = process_data(original_data)

    # 提取所有 level_name
    level_names = []
    for item in data:
        level_names.extend(item["level_name"])

    if not os.path.exists(class_url):
        logging.error(f"错误: 未找到 {class_url} 文件")  # 写入日志文件
        tqdm.write(f"错误: 未找到 {class_url} 文件")
        return

    # 读取 m3u8 地址列表
    with open(class_url, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        logging.error("错误: 文件中没有有效的 m3u8 地址")  # 写入日志文件
        tqdm.write("错误: 文件中没有有效的 m3u8 地址")
        return

    # 输出总视频数
    tqdm.write(f"总视频数: {len(urls)}")

    # 遍历并下载每个视频
    for i, url in enumerate(urls, 1):
        # 使用 level_name 作为文件名（如果存在），否则使用默认文件名
        if i <= len(level_names):
            output_file = os.path.join(output_dir, f"{level_names[i-1]}.mp4")
        else:
            output_file = os.path.join(output_dir, f"video_{i:03d}.mp4")

        if os.path.exists(output_file):
            logging.info(f"跳过: {output_file} 已存在")  # 写入日志文件
            tqdm.write(f"跳过: {output_file} 已存在")
            continue

        if not download_video(url, output_file, i, len(urls), timeout):
            tqdm.write(f"跳过第 {i} 个视频: {url}")
        time.sleep(2)

if __name__ == "__main__":
    main()