# 中公网课视频下载

### 目录结构
```bash
├── README.md
├── class_download.py
├── class_src.json  # 课程大纲下的每个视频课程详细信息, 用于提取视频课程名称
├── class_url.txt  # 具体课程的 api m3u8 地址, 用于下载视频片段并合并视频
└── config.json  # 配置文件, 保持默认即可
```

### 容器执行环境
```bash
registry.cn-hangzhou.aliyuncs.com/basex/aria2c:1.0.0

docker run -itd --name aria2c registry.cn-hangzhou.aliyuncs.com/basex/aria2c:1.0.0
```

### 1. 获取 class_src.json
```bash
1. 打开学习课程大纲页面, 链接如: https://xue.eoffcn.com/web/study_package.html?package_id=622629&course_type=1&system_order=X240410160739888049&coding=cid1098876
2. F12 打开浏览器开发者工具, 过滤只显示 Fetch/XHR, 找到这样的链接如: https://xue.eoffcn.com/api/lesson/catagory?package_id=622629&system_order=X240431160739888049
3. 选择链接右侧依次找到 Preview -> data -> outline_info, 右键 outline_info, 选择 Copy value 复制该 json 格式数据
4. 本地保存第 3 步复制的 json 数据, 文件名为 class_src.json
```

### 2. 获取 class_url.txt
```bash
1. 还是在学习课程大纲页面, 打开具体是视频学习页面, 链接如: https://xue.eoffcn.com/web/video.html?lesson_id=9161581&package_id=622629&course_type=1&coding=cid1098876&system_order=X240410160739888049&is_task=2
2. 同样 F12 打开浏览器开发者工具, 过滤只显示 Fetch/XHR, 找到课程的 api m3u8 地址, 链接如: https://api.eoffcn.com/chain/video/play/mda-b545ee5bc15563fdeb1d297e949adde0.m3u8?ak=142872f208f98da991a5367623bdbef1&ext=eyJleHBpcmUiOjg2NDAwLCJzZWs1cml0eSI6ImNoYWluIn0%3D&sign=ea0d2da99e779c8e03591f287b1ccd13&t=1742275410
3. 复制 api m3u8 地址, 本地保存文件名为 class_url.txt
```

### 执行命令
```bash
python3 class_download.py
```

### 下载过程
```bash
总视频数: 2
正在下载第 1 个视频: 导学1.mp4
下载完成! 视频保存路径：videos/导学1.mp4 ✅
正在下载第 2 个视频: 导学2.mp4
下载完成! 视频保存路径：videos/导学2.mp4 ✅
```

### 参考
```bash
方法一:
使用 ffmpeg 直接下载并合并
ffmpeg -i "https://api.eoffcn.com/chain/video/play/mda-0339b8bc5484c363462bafdfe5d62deb.m3u8?ak=xxxxxx&ext=xxxxxx&sign=8477af1726f2040ac6b80987c44c0228&t=1742438571" -c copy output.mp4
✅ 优点：自动解析 m3u8，合并所有 ts 片段，直接生成 mp4 文件。

方法二:
1. 使用 aria2c 批量下载 .ts 文件 如果 ffmpeg 速度慢，可以手动下载 .m3u8 并用 aria2c 下载所有 .ts 片段：
curl -o video.m3u8 "https://api.eoffcn.com/chain/video/play/mda-0339b8bc5484c363462bafdfe5d62deb.m3u8?ak=xxxxxx&ext=xxxxxx&sign=8477af1726f2040ac6b80987c44c0228&t=1742438571"

2. 然后解析 .m3u8 并用 aria2c 下载：
cat video.m3u8 | grep ".ts" > ts_list.txt
aria2c -i ts_list.txt -j 16  # 16 线程下载

3. 最后用 ffmpeg 合并：
ffmpeg -i "concat:$(ls *.ts | tr '\n' '|')" -c copy output.mp4
✅ 优点：aria2c 速度快，支持断点续传。
```