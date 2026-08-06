#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""describe-image: 用视觉模型把图片转述成文字。

当宿主模型没有视觉能力时（例如 DeepSeek、某些本地模型），用户粘贴的图片
在对话中只会变成 [Image: ...] / [Unsupported Image] 之类占位符。本脚本把图片
发给一个独立的视觉模型（OpenAI 兼容 API 或本地 Ollama），把识别结果以文字
返回，供宿主模型在此基础上推理和回复。

用法:
  python describe_image.py --setup                     # 首次配置向导
  python describe_image.py <图片路径或URL> [更多图片...]
  python describe_image.py --prompt "具体问题" <图片路径或URL> [...]
  python describe_image.py                             # 自动从最近的会话记录提取图片

配置优先级: 环境变量 > config.json > 内置默认值。
环境变量(通用名称, 与具体平台无关):
  DESCRIBE_IMAGE_BASE_URL   例如 https://api.siliconflow.cn/v1
  DESCRIBE_IMAGE_API_KEY    平台 API Key（也可以只放 config.json）
  DESCRIBE_IMAGE_MODEL      视觉模型名

注意: config.json 含 API Key，已在 .gitignore 中排除，切勿提交到仓库。
"""

import argparse
import base64
import getpass
import glob
import json
import os
import sys
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# OpenAI 兼容 chat/completions 端点
API_PATH = "/chat/completions"

MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".avif": "image/avif",
    ".tiff": "image/tiff",
}

DEFAULT_PROMPT = (
    "请详细、准确地描述这张图片的内容：包括所有可见的文字(逐字转录)、物体、人物、"
    "场景、布局、颜色和任何值得注意的细节。"
)

# 常见平台的 OpenAI 兼容配置预设（模型名仅为默认值，可按需修改）
PROVIDER_PRESETS = {
    "siliconflow": {
        "name": "SiliconFlow 硅基流动",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
        "needs_key": True,
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "needs_key": True,
    },
    "moonshot": {
        "name": "Moonshot / Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "kimi-latest",
        "needs_key": True,
    },
    "zhipu": {
        "name": "智谱 AI (BigModel)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4v-flash",
        "needs_key": True,
    },
    "dashscope": {
        "name": "阿里云百炼 (DashScope)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-vl-plus",
        "needs_key": True,
    },
    "ollama": {
        "name": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5vl:7b",
        "needs_key": False,
    },
    "custom": {
        "name": "自定义 (任意 OpenAI 兼容端点)",
        "base_url": "",
        "model": "",
        "needs_key": True,
    },
}

# 粘贴的图片存放在会话 transcript 中。Claude Code 路径:
#   ~/.claude/projects/<工作目录>/<会话ID>.jsonl
# 图片以 {"type":"image","source":{"type":"base64","media_type":None,"data":"<base64>"}}
# 形式存在。opencode 额外会把粘贴图片落盘到 %LOCALAPPDATA%\Temp\opencode\。
TRANSCRIPT_GLOBS = [
    os.path.join(os.path.expanduser("~"), ".claude", "projects", "**", "*.jsonl"),
]
OPENCODE_TEMP_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Temp", "opencode"
)


def default_config():
    return {
        "provider": "siliconflow",
        "base_url": PROVIDER_PRESETS["siliconflow"]["base_url"],
        "model": PROVIDER_PRESETS["siliconflow"]["model"],
        "api_key": "",
        "max_tokens": 1000,
        "temperature": 0.7,
        "default_prompt": DEFAULT_PROMPT,
    }


def load_config():
    cfg = default_config()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"[describe-image] 警告: config.json 读取失败({e})，使用默认值", file=sys.stderr)
    # 环境变量优先，名称与平台无关
    cfg["api_key"] = os.environ.get("DESCRIBE_IMAGE_API_KEY") or cfg.get("api_key", "")
    cfg["base_url"] = os.environ.get("DESCRIBE_IMAGE_BASE_URL") or cfg.get("base_url", "")
    cfg["model"] = os.environ.get("DESCRIBE_IMAGE_MODEL") or cfg.get("model", "")
    return cfg


def _prompt(text):
    """交互输入；输入流关闭时优雅退出，而不是抛 EOFError 堆栈。"""
    try:
        return input(text).strip()
    except EOFError:
        print("\n[describe-image] 配置向导已取消（输入流已关闭）。", file=sys.stderr)
        sys.exit(0)


def run_setup():
    """首次配置向导：交互式写入 config.json。"""
    cfg = load_config()
    print("== describe-image 配置向导 ==")
    print("将把配置写入:", CONFIG_PATH)
    print()

    print("请选择视觉模型平台:")
    keys = list(PROVIDER_PRESETS.keys())
    for i, k in enumerate(keys, 1):
        p = PROVIDER_PRESETS[k]
        print(f"  {i}) {p['name']}  (模型默认: {p['model'] or '自定义'})")
    choice = _prompt(f"输入序号 [1-{len(keys)}, 回车默认 1]: ")
    try:
        key = keys[int(choice) - 1]
    except (ValueError, IndexError):
        key = "siliconflow"
    preset = PROVIDER_PRESETS[key]
    cfg["provider"] = key

    default_url = preset["base_url"]
    url = _prompt(f"Base URL [回车默认 {default_url}]: ")
    # custom 平台没有默认 URL，必须显式填写
    while not (url or default_url):
        print("[describe-image] 自定义平台必须填写 Base URL（例如 https://api.example.com/v1）", file=sys.stderr)
        url = _prompt("Base URL: ")
    cfg["base_url"] = url or default_url

    # custom 平台没有默认模型，必须显式填写；其他平台用预设或旧 config 兜底
    if key == "custom":
        default_model = ""
    elif preset["model"]:
        default_model = preset["model"]
    else:
        default_model = cfg.get("model", "")
    model = _prompt(f"视觉模型名 [回车默认 {default_model or '(必填)'}]: ")
    while not (model or default_model):
        print("[describe-image] 自定义平台必须填写视觉模型名（例如 my-vision-model）", file=sys.stderr)
        model = _prompt("视觉模型名: ")
    cfg["model"] = model or default_model

    if preset["needs_key"]:
        try:
            key_help = getpass.getpass("API Key (不回显) [回车跳过，改用环境变量 DESCRIBE_IMAGE_API_KEY]: ").strip()
        except EOFError:
            print("\n[describe-image] 配置向导已取消（输入流已关闭）。", file=sys.stderr)
            sys.exit(0)
        if key_help:
            cfg["api_key"] = key_help
    else:
        cfg["api_key"] = ""

    max_tokens = _prompt(f"max_tokens [回车默认 {cfg.get('max_tokens', 1000)}]: ")
    if max_tokens.isdigit():
        cfg["max_tokens"] = int(max_tokens)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print()
    print("已写入配置。快速验证:")
    print(f'  python "{os.path.join(SCRIPT_DIR, os.path.basename(__file__))}" --test')
    print("或直接转述一张图片: python describe_image.py <图片路径>")


def to_image_url(p):
    p = p.strip()
    if p.startswith(("http://", "https://")):
        return p
    if not os.path.exists(p):
        raise FileNotFoundError(f"找不到图片文件: {p}")
    ext = os.path.splitext(p)[1].lower()
    mime = MIME.get(ext)
    if not mime:
        raise ValueError(f"不支持的图片格式: {ext or '(无扩展名)'} (支持: {', '.join(sorted(MIME))})")
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _sniff_mime(data_b64):
    head = base64.b64decode(data_b64[:16] + "=" * ((4 - len(data_b64[:16]) % 4) % 4))
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:2] == b"\xff\xd8":
        return "image/jpeg"
    if head[:4] in (b"GIF8",):
        return "image/gif"
    if head[:4] == b"RIFF" and data_b64[8:12] == "WEBP":
        return "image/webp"
    if head[:2] == b"BM":
        return "image/bmp"
    return "image/png"


def extract_images_from_transcript(transcript):
    """从 Claude Code / opencode 的会话 transcript(.jsonl) 中提取所有图片块。

    返回 [(mime, base64data), ...]。
    """
    images = []
    try:
        with open(transcript, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = None
                if isinstance(obj, dict) and obj.get("type") == "user":
                    msg = obj.get("message") or {}
                    content = msg.get("content")
                elif isinstance(obj, dict) and obj.get("type") == "message":
                    content = obj.get("content")
                if isinstance(content, str):
                    continue
                if not isinstance(content, list):
                    continue
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != "image":
                        continue
                    src = item.get("source") or {}
                    if src.get("type") != "base64":
                        continue
                    data = (src.get("data") or "").strip()
                    if not data:
                        continue
                    mime = src.get("media_type") or item.get("media_type") or _sniff_mime(data)
                    if data.startswith("data:"):
                        data = data.split(",", 1)[1]
                    images.append((mime, data))
    except Exception as e:
        print(f"[describe-image] 警告: 读取 transcript {transcript} 失败: {e}", file=sys.stderr)
    return images


def find_candidates():
    """按修改时间倒序返回候选来源：会话 transcript 与 opencode 粘贴图片目录。"""
    found = []
    for pat in TRANSCRIPT_GLOBS:
        found.extend(glob.glob(pat, recursive=True))
    if os.path.isdir(OPENCODE_TEMP_DIR):
        for ext in MIME:
            found.extend(glob.glob(os.path.join(OPENCODE_TEMP_DIR, "*" + ext)))
    seen, uniq = set(), []
    for f in sorted(found, key=lambda p: os.path.getmtime(p), reverse=True):
        if f in seen:
            continue
        seen.add(f)
        uniq.append(f)
    return uniq


def chat_completion(base_url, api_key, payload):
    url = base_url.rstrip("/") + API_PATH
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"API 错误 {e.code}: {body}")
    except Exception as e:
        raise RuntimeError(f"请求失败: {e}")


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="用视觉模型把图片转述成文字", add_help=True)
    ap.add_argument("--setup", action="store_true", help="运行首次配置向导")
    ap.add_argument("--test", action="store_true", help="用一张内置测试图验证配置是否可用")
    ap.add_argument("--print-config", action="store_true", help="打印当前配置(API Key 打码)")
    ap.add_argument("--prompt", default="", help="转述提示词；缺省用 config.json 的 default_prompt")
    ap.add_argument("--transcript", default=None, help="从指定会话 transcript(.jsonl) 提取图片")
    ap.add_argument("images", nargs="*", help="图片本地路径或 http(s) 链接")
    args = ap.parse_args()

    if args.setup:
        run_setup()
        return

    cfg = load_config()
    if args.print_config:
        shown = dict(cfg)
        key = shown.get("api_key", "")
        shown["api_key"] = (key[:4] + "****" + key[-4:]) if len(key) > 8 else "****"
        print(json.dumps(shown, ensure_ascii=False, indent=2))
        return

    # 配置校验（--test 与正常转述共用）
    if not cfg.get("api_key") and not cfg.get("base_url", "").lower().startswith("http://localhost"):
        print("[describe-image] 错误: 未配置 API Key。")
        print("  首次使用请运行: python describe_image.py --setup")
        print("  或设置环境变量 DESCRIBE_IMAGE_API_KEY，或在 config.json 中填写 api_key。", file=sys.stderr)
        sys.exit(1)
    if not cfg.get("model"):
        print("[describe-image] 错误: 未配置模型名 (model)。请运行 --setup 或设置 DESCRIBE_IMAGE_MODEL。", file=sys.stderr)
        sys.exit(1)

    if args.test:
        # 用一张内置的 64x64 纯红测试图验证配置可用（合法 PNG，满足常见 VL 模型最小尺寸）
        test_png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAb0lEQVR4nO3PAQkAAAyEwO9f"
            "eoshgnABdLep8QUNyPEFDcjxBQ3I8QUNyPEFDcjxBQ3I8QUNyPEFDcjxBQ3I8QUNyPEFDcjx"
            "BQ3I8QUNyPEFDcjxBQ3I8QUNyPEFDcjxBQ3I8QUNyPEFDcjxBQ3IPanc8OLDQitxAAAAAElF"
            "TkSuQmCC"
        )
        content = [
            {"type": "text", "text": "回复 OK 表示图片正常接收"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + test_png_b64}},
        ]
        payload = {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 50,
            "temperature": 0,
        }
        try:
            data = chat_completion(cfg["base_url"], cfg.get("api_key", ""), payload)
        except RuntimeError as e:
            print(f"[describe-image] 配置测试失败: {e}", file=sys.stderr)
            sys.exit(1)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            print(f"[describe-image] 配置测试失败，响应异常: {json.dumps(data, ensure_ascii=False)[:300]}", file=sys.stderr)
            sys.exit(1)
        print("配置测试通过，视觉模型返回:")
        print(text)
        return

    prompt = args.prompt or cfg.get("default_prompt") or DEFAULT_PROMPT
    content = [{"type": "text", "text": prompt}]

    if args.images:
        for p in args.images:
            try:
                content.append({"type": "image_url", "image_url": {"url": to_image_url(p)}})
            except (FileNotFoundError, ValueError) as e:
                print(f"[describe-image] 错误: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        candidates = [args.transcript] if args.transcript else find_candidates()
        used, images = set(), []
        for cand in candidates:
            if not cand or cand in used:
                continue
            used.add(cand)
            ext = os.path.splitext(cand)[1].lower()
            if ext in MIME:
                try:
                    with open(cand, "rb") as f:
                        images = [(MIME[ext], base64.b64encode(f.read()).decode("ascii"))]
                except OSError as e:
                    print(f"[describe-image] 警告: 读取图片 {cand} 失败: {e}", file=sys.stderr)
                    continue
                if images:
                    print(f"[describe-image] 从粘贴图片目录提取到图片: {cand}", file=sys.stderr)
                    break
            imgs = extract_images_from_transcript(cand)
            if imgs:
                images = imgs
                print(f"[describe-image] 从 transcript 提取到 {len(imgs)} 张图片: {cand}", file=sys.stderr)
                break
        if not images:
            print("[describe-image] 错误: 未提供图片，且没在会话记录/粘贴目录中找到图片。")
            print("请传入图片路径，或重新粘贴图片后重试。", file=sys.stderr)
            sys.exit(1)
        for mime, data in images:
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})

    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": content}],
        "max_tokens": int(cfg.get("max_tokens", 1000)),
        "temperature": float(cfg.get("temperature", 0.7)),
    }

    try:
        data = chat_completion(cfg["base_url"], cfg.get("api_key", ""), payload)
    except RuntimeError as e:
        print(f"[describe-image] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"[describe-image] 响应异常: {json.dumps(data, ensure_ascii=False)[:500]}", file=sys.stderr)
        sys.exit(1)

    print(text)


if __name__ == "__main__":
    main()
