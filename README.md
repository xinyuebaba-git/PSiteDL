# PSiteDL

PSiteDL 是一个网页视频切片探测与下载工具，支持命令行和图形界面。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## 命令行

```bash
psitedl "https://example.com/video-page" \
  --output-dir "$HOME/Downloads" \
  --browser chrome \
  --profile Default \
  --capture-seconds 30
```

批量 URL 文本输入：

```bash
psitedl --url-file "/absolute/path/PDL.txt" --output-dir "$HOME/Downloads"
```

## GUI

```bash
psitedl-gui
```

## 打包部署

```bash
python3 scripts/build_psitedl_bundle.py
```

在目标机器解压后：

```bash
python3 deploy_psitedl_bundle.py --bundle-dir .
./run_psitedl.sh --url-file /absolute/path/PDL.txt
./run_psitedl_gui.sh
```
