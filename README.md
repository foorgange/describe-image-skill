# describe-image

让没有视觉能力的模型也能"看懂"图片：把图片发给一个独立的视觉模型转述成文字，再由你的宿主模型基于这段文字回答。

如果你用的模型不接收图片（例如 DeepSeek、部分本地模型），用户在对话里粘贴截图时，你只能看到 `[Image: ...]`、`[Unsupported Image]` 这类占位符，看不到像素。这个技能就是为这种情况准备的：它把图片交给一个视觉模型（SiliconFlow / OpenAI / Ollama / 其他兼容端点），把识别结果以纯文本返回，你再用这段文本回答用户。

适用场景：截图内容识别、图片里的文字转录、UI 界面描述、图表/文档/照片解读，以及一切"图片里有什么"的问题。

## 为什么需要它

- 你的宿主模型没有视觉能力（DeepSeek、某些本地模型等）。
- 用户粘贴了图片，但你能拿到的只是占位符文本，图片本体只在底层会话记录里。
- 你不想因为一张图换掉整个模型，只想在需要的时候临时调用一个视觉模型。

本技能不要求你换模型、不要求宿主环境支持图片，只要求本机有 Python 3.8+ 和一个可用的视觉模型端点。

## 特性

- 支持任意 OpenAI 兼容的 `/chat/completions` 端点，内置常见平台预设：SiliconFlow、OpenAI、Moonshot/Kimi、智谱、阿里云百炼，以及本地 Ollama。
- 首次使用有交互式配置向导 `--setup`，自动写入 `config.json`。
- 支持三种图片来源：
  - 显式传入本地路径或 URL。
  - 自动从最近的会话记录（transcript）提取粘贴的图片——Claude Code 与 opencode 都支持。
  - opencode 粘贴图片的落盘目录兜底。
- 纯 Python 标准库，零第三方依赖。
- 配置优先级：环境变量 > `config.json` > 内置默认值。

## 安装

把本仓库克隆（或复制）到你的技能目录。以 Claude Code 为例，技能目录是 `~/.claude/skills/`：

```powershell
# 用 git 克隆到技能目录
cd ~\.claude\skills
git clone https://github.com/foorgange/describe-image-skill.git describe-image
```

对于 opencode：技能目录是 `~/.config/opencode/skills/`，同样把 `describe-image` 这个文件夹放进去即可（或用 `~/.claude/skills` 下的共享技能，取决于你的 opencode 版本是否扫描该目录）。

装好后确认目录结构：

```text
describe-image/
├── SKILL.md            # 技能说明（宿主模型读取）
├── describe_image.py   # 转述脚本
├── config.json         # 你的配置（含 API Key，不入库）
├── config.example.json # 配置模板
└── README.md
```

## 配置

### 首次配置向导

```powershell
cd ~\.claude\skills\describe-image
python describe_image.py --setup
```

向导会依次询问：

1. 视觉模型平台（SiliconFlow / OpenAI / Moonshot / 智谱 / 阿里云百炼 / Ollama / 自定义）。
2. Base URL（有默认值，直接回车即可）。
3. 视觉模型名（有默认值，可改）。
4. API Key（不回显）。选择 Ollama 时不需要 Key。

配置写入技能目录下的 `config.json`。**这个文件已被 `.gitignore` 排除，不会被提交**。

也可以用环境变量覆盖（优先级最高，适合不想把 Key 写进文件的情况）：

```powershell
$env:DESCRIBE_IMAGE_BASE_URL = "https://api.siliconflow.cn/v1"
$env:DESCRIBE_IMAGE_API_KEY = "sk-..."
$env:DESCRIBE_IMAGE_MODEL   = "Qwen/Qwen3-VL-30B-A3B-Instruct"
```

### 验证配置

```powershell
python describe_image.py --test
```

会生成一张内置测试图（上面画了一行字）并转述，用来确认端点、Key、模型是否都可用。

### 支持的平台参考值

| 平台 | Base URL | 示例模型 | 需要 Key |
|---|---|---|---|
| SiliconFlow | `https://api.siliconflow.cn/v1` | `Qwen/Qwen3-VL-30B-A3B-Instruct` | 是 |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | 是 |
| Moonshot | `https://api.moonshot.cn/v1` | `kimi-latest` | 是 |
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v-flash` | 是 |
| 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` | 是 |
| Ollama（本地） | `http://localhost:11434/v1` | `qwen2.5vl:7b` | 否 |

表中模型名只是默认值，按你实际的可用模型改即可。任何 OpenAI 兼容端点都能用 `custom` 预设接入。

## 用法

### 转述一张图片（显式路径）

```powershell
python describe_image.py "C:\path\to\image.png"
python describe_image.py "C:\a.png" "C:\b.jpg"          # 多张
python describe_image.py "https://example.com/x.png"     # 远程 URL
```

### 转述粘贴进对话的图片（自动提取）

在你的 Claude Code / opencode 会话里粘贴图片后，不带任何图片参数直接运行：

```powershell
python describe_image.py
```

脚本会扫描最近的会话记录，找到最新粘贴的那张图并转述。这样你在对话里面对 `[Image: ...]` 占位符时也能转述——这就是本技能的主要使用方式。

### 带具体问题

```powershell
python describe_image.py --prompt "图里写的什么字？请逐字转录"
```

### 手动指定会话记录

```powershell
python describe_image.py --transcript "C:\Users\you\.claude\projects\your-project\<session>.jsonl"
```

### 查看当前配置（Key 打码）

```powershell
python describe_image.py --print-config
```

## 在 Claude Code / opencode 中自动触发

本技能通过 `SKILL.md` 让宿主模型知道什么时候调用它：

- 用户贴图、提到图片路径、说"看图/截图里有什么/识别这张图"，或者消息里出现 `[Image: ...]`、`[Unsupported Image]`、`[图片:` 占位符时，先运行本脚本转述，再基于文字回答。
- 首次加载技能时，会尝试在你的宿主环境记忆文件里写入一条"图片先走 describe-image 转述"的提醒，避免以后漏掉。该写入是幂等的，不会重复。

如果你的宿主环境（例如某些 opencode 版本）扫描不到 `~/.claude/skills`，把 `describe-image` 文件夹放进该环境自己的技能目录即可。

## 它是怎么工作的

1. 宿主模型判定"这是一张图，但我看不见"。
2. 运行 `describe_image.py`：
   - 有显式路径/URL 就用它；
   - 否则从最近的会话记录（transcript）里找到粘贴图片的 base64 数据。
3. 脚本把图片和提示词一起发给视觉模型（OpenAI 兼容格式）。
4. 视觉模型返回文字描述，脚本打印到 stdout。
5. 宿主模型读取这段文字，回答用户的问题。

提取粘贴图片的机制：Claude Code 会把粘贴的图片以 `{"type":"image","source":{"type":"base64",...}}` 存在 `~/.claude/projects/**/*.jsonl` 会话记录里；opencode 除了同样存在 transcript，还会把图片落到 `%LOCALAPPDATA%\Temp\opencode\`。脚本两个位置都会找，取最新的。

## 安全

- `config.json` 含你的 API Key，已在 `.gitignore` 排除。提交/推送前请确认仓库里没有 `config.json`。
- 脚本不会把 Key 写进日志或响应。
- 图片通过 HTTPS 发给视觉模型端点，仅用于本次转述，不落盘（粘贴图片的临时文件由宿主环境管理）。

## 常见问题

**提示"未配置 API Key"**
先运行 `python describe_image.py --setup`，或设置 `DESCRIBE_IMAGE_API_KEY`。

**提示"没在会话记录/粘贴目录中找到图片"**
你还没贴图，或者图不在最近的会话里。直接传入图片路径，或重新粘贴后重试。

**`--test` 失败**
检查 Base URL 是否以 `/v1` 结尾、模型名是否对当前平台有效、Key 是否有权限、网络是否能连通该端点。

**宿主模型仍不自动触发转述**
确认 `SKILL.md` 已随技能目录加载；若环境不扫描该目录，放到对应技能目录。也可以在对话里手动运行脚本。

## 开发与贡献

- 脚本零第三方依赖，逻辑在 `describe_image.py` 单文件内。
- 改动后自测：`python describe_image.py --test` 和显式路径转述。
- 提交时不要带上 `config.json`。
- 欢迎提 issue / PR 补充新的平台预设。

## License

[MIT](LICENSE)
