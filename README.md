# describe-image

Let non-vision models "see" images: hand the image to a separate vision model, get its description as text, and let your host model answer from that text.

让没有视觉能力的模型也能"看懂"图片：把图片交给一个独立的视觉模型转述成文字，再由你的宿主模型基于这段文字回答。

If your model does not accept images (e.g. DeepSeek, some local models), pasted screenshots only appear to you as `[Image: ...]` / `[Unsupported Image]` placeholders — you never see the pixels. This skill is built for exactly that case: it forwards the image to a vision model (SiliconFlow / OpenAI / Ollama / any OpenAI-compatible endpoint) and returns the recognition result as plain text that you can reason over.

如果你的模型不接收图片（例如 DeepSeek、部分本地模型），用户在对话里粘贴截图时，你只能看到 `[Image: ...]`、`[Unsupported Image]` 这类占位符，看不到像素。这个技能就是为这种情况准备的：它把图片交给一个视觉模型（SiliconFlow / OpenAI / Ollama / 任意 OpenAI 兼容端点），把识别结果以纯文本返回，你再用这段文本回答用户。

Use cases: screenshot content recognition, transcribing text inside images, UI description, interpreting charts / documents / photos, and any "what is in this image" question.

适用场景：截图内容识别、图片里的文字转录、UI 界面描述、图表/文档/照片解读，以及一切"图片里有什么"的问题。

## Why / 为什么需要它

- Your host model has no vision capability (DeepSeek, certain local models, etc.).
- 你的宿主模型没有视觉能力（DeepSeek、某些本地模型等）。
- The user pasted an image, but all you get is a placeholder; the actual pixels only live in the session transcript.
- 用户粘贴了图片，但你能拿到的只是占位符文本，图片本体只在底层会话记录里。
- You do not want to switch models over a single image — you just want to call a vision model on demand.
- 你不想因为一张图换掉整个模型，只想在需要的时候临时调用一个视觉模型。

This skill does not require you to change models or to have a host that supports images. It only requires Python 3.8+ and a reachable vision-model endpoint.

本技能不要求你换模型、不要求宿主环境支持图片，只要求本机有 Python 3.8+ 和一个可用的视觉模型端点。

## Features / 特性

- Supports any OpenAI-compatible `/chat/completions` endpoint, with built-in presets: SiliconFlow, OpenAI, Moonshot/Kimi, Zhipu, Alibaba Cloud (DashScope), and local Ollama.
- 支持任意 OpenAI 兼容的 `/chat/completions` 端点，内置常见平台预设：SiliconFlow、OpenAI、Moonshot/Kimi、智谱、阿里云百炼，以及本地 Ollama。
- Interactive first-run wizard `--setup` that writes `config.json`.
- 首次使用有交互式配置向导 `--setup`，自动写入 `config.json`。
- Three image sources:
  - 支持三种图片来源：
  - Explicit local path or URL.
  - 显式传入本地路径或 URL。
  - Auto-extract pasted images from recent session transcripts (Claude Code and opencode).
  - 自动从最近的会话记录（transcript）提取粘贴的图片——Claude Code 与 opencode 都支持。
  - Fallback to opencode's pasted-image drop directory.
  - opencode 粘贴图片的落盘目录兜底。
- Pure Python standard library, zero third-party dependencies.
- 纯 Python 标准库，零第三方依赖。
- Config precedence: environment variables > `config.json` > built-in defaults.
- 配置优先级：环境变量 > `config.json` > 内置默认值。

## Installation / 安装

Clone (or copy) this repo into your skills directory. For Claude Code, the skills directory is `~/.claude/skills/`:

把本仓库克隆（或复制）到你的技能目录。以 Claude Code 为例，技能目录是 `~/.claude/skills/`：

```powershell
# Clone into the skills directory / 用 git 克隆到技能目录
cd ~\.claude\skills
git clone https://github.com/foorgange/describe-image-skill.git describe-image
```

For opencode, the skills directory is `~/.config/opencode/skills/` — put the `describe-image` folder there (or rely on shared skills under `~/.claude/skills`, depending on whether your opencode version scans that directory).

对于 opencode：技能目录是 `~/.config/opencode/skills/`，同样把 `describe-image` 这个文件夹放进去即可（或用 `~/.claude/skills` 下的共享技能，取决于你的 opencode 版本是否扫描该目录）。

Expected layout / 装好后确认目录结构：

```text
describe-image/
├── SKILL.md            # Skill instructions (read by the host model) / 技能说明（宿主模型读取）
├── describe_image.py   # Transcription script / 转述脚本
├── config.json         # Your config (contains API key, not committed) / 你的配置（含 API Key，不入库）
├── config.example.json # Config template / 配置模板
└── README.md
```

## Configuration / 配置

### First-run wizard / 首次配置向导

```powershell
cd ~\.claude\skills\describe-image
python describe_image.py --setup
```

The wizard asks, in order / 向导会依次询问：

1. Vision-model provider (SiliconFlow / OpenAI / Moonshot / Zhipu / DashScope / Ollama / custom).
   视觉模型平台（SiliconFlow / OpenAI / Moonshot / 智谱 / 阿里云百炼 / Ollama / 自定义）。
2. Base URL (has a default — press Enter to accept).
   Base URL（有默认值，直接回车即可）。
3. Vision model name (has a default; change it as needed).
   视觉模型名（有默认值，可改）。
4. API key (not echoed). Not required when Ollama is selected.
   API Key（不回显）。选择 Ollama 时不需要 Key。

The config is written to `config.json` in the skill directory. **This file is excluded by `.gitignore` and will never be committed.**

配置写入技能目录下的 `config.json`。**这个文件已被 `.gitignore` 排除，不会被提交**。

You can also configure via environment variables (highest precedence, handy when you do not want the key in a file):

也可以用环境变量覆盖（优先级最高，适合不想把 Key 写进文件的情况）：

```powershell
$env:DESCRIBE_IMAGE_BASE_URL = "https://api.siliconflow.cn/v1"
$env:DESCRIBE_IMAGE_API_KEY = "sk-..."
$env:DESCRIBE_IMAGE_MODEL   = "Qwen/Qwen3-VL-30B-A3B-Instruct"
```

### Verify the config / 验证配置

```powershell
python describe_image.py --test
```

Sends a built-in test image to the endpoint to confirm that the URL, key, and model all work.

会用内置测试图发一次请求，用来确认端点、Key、模型是否都可用。

### Provider reference / 支持的平台参考值

| Provider / 平台 | Base URL | Example model / 示例模型 | Needs key / 需要 Key |
|---|---|---|---|
| SiliconFlow | `https://api.siliconflow.cn/v1` | `Qwen/Qwen3-VL-30B-A3B-Instruct` | Yes / 是 |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | Yes / 是 |
| Moonshot | `https://api.moonshot.cn/v1` | `kimi-latest` | Yes / 是 |
| Zhipu AI / 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v-flash` | Yes / 是 |
| Alibaba DashScope / 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` | Yes / 是 |
| Ollama (local / 本地) | `http://localhost:11434/v1` | `qwen2.5vl:7b` | No / 否 |

The model names above are only defaults — adjust them to what your provider actually offers. Any OpenAI-compatible endpoint can be connected via the `custom` preset.

表中模型名只是默认值，按你实际的可用模型改即可。任何 OpenAI 兼容端点都能用 `custom` 预设接入。

## Usage / 用法

### Transcribe one image (explicit path) / 转述一张图片（显式路径）

```powershell
python describe_image.py "C:\path\to\image.png"
python describe_image.py "C:\a.png" "C:\b.jpg"          # multiple images / 多张
python describe_image.py "https://example.com/x.png"     # remote URL / 远程 URL
```

### Transcribe a pasted image (auto-extract) / 转述粘贴进对话的图片（自动提取）

After you paste an image in your Claude Code / opencode session, run with no image argument:

在你的 Claude Code / opencode 会话里粘贴图片后，不带任何图片参数直接运行：

```powershell
python describe_image.py
```

The script scans recent session transcripts, finds the most recently pasted image, and transcribes it. This is the primary way to use the skill when you are facing an `[Image: ...]` placeholder.

脚本会扫描最近的会话记录，找到最新粘贴的那张图并转述。这样你在对话里面对 `[Image: ...]` 占位符时也能转述——这就是本技能的主要使用方式。

### With a specific question / 带具体问题

```powershell
python describe_image.py --prompt "图里写的什么字？请逐字转录"
```

### Point at a specific transcript / 手动指定会话记录

```powershell
python describe_image.py --transcript "C:\Users\you\.claude\projects\your-project\<session>.jsonl"
```

### Show current config (key masked) / 查看当前配置（Key 打码）

```powershell
python describe_image.py --print-config
```

## Auto-trigger in Claude Code / opencode

本技能通过 `SKILL.md` 让宿主模型知道什么时候调用它。

The skill uses `SKILL.md` to tell the host model when to invoke it:

- When the user pastes an image, mentions an image path, says "look at this image / what is in this screenshot / recognize this image", or the message contains `[Image: ...]`, `[Unsupported Image]`, `[图片:` placeholders, first run the script to transcribe, then answer from the text.
- 用户贴图、提到图片路径、说"看图/截图里有什么/识别这张图"，或者消息里出现 `[Image: ...]`、`[Unsupported Image]`、`[图片:` 占位符时，先运行本脚本转述，再基于文字回答。
- On first load, the skill tries to write a "route images through describe-image first" reminder into your host environment's memory file, so future sessions do not miss it. The write is idempotent.
- 首次加载技能时，会尝试在你的宿主环境记忆文件里写入一条"图片先走 describe-image 转述"的提醒，避免以后漏掉。该写入是幂等的，不会重复。

If your host environment (e.g. some opencode versions) does not scan `~/.claude/skills`, put the `describe-image` folder into that environment's own skills directory.

如果你的宿主环境（例如某些 opencode 版本）扫描不到 `~/.claude/skills`，把 `describe-image` 文件夹放进该环境自己的技能目录即可。

## How it works / 它是怎么工作的

1. The host model decides "this is an image, but I cannot see it".
   宿主模型判定"这是一张图，但我看不见"。
2. Run `describe_image.py`:
   运行 `describe_image.py`：
   - With an explicit path/URL, use it.
   - 有显式路径/URL 就用它；
   - Otherwise, pull the pasted image's base64 data from the most recent session transcript.
   - 否则从最近的会话记录（transcript）里找到粘贴图片的 base64 数据。
3. The script sends the image and prompt to the vision model (OpenAI-compatible format).
   脚本把图片和提示词一起发给视觉模型（OpenAI 兼容格式）。
4. The vision model returns a text description; the script prints it to stdout.
   视觉模型返回文字描述，脚本打印到 stdout。
5. The host model reads that text and answers the user.
   宿主模型读取这段文字，回答用户的问题。

How pasted images are located: Claude Code stores pasted images as `{"type":"image","source":{"type":"base64",...}}` inside `~/.claude/projects/**/*.jsonl` session transcripts; opencode stores them in transcripts too and also drops image files into `%LOCALAPPDATA%\Temp\opencode\`. The script checks both locations and uses the newest one.

提取粘贴图片的机制：Claude Code 会把粘贴的图片以 `{"type":"image","source":{"type":"base64",...}}` 存在 `~/.claude/projects/**/*.jsonl` 会话记录里；opencode 除了同样存在 transcript，还会把图片落到 `%LOCALAPPDATA%\Temp\opencode\`。脚本两个位置都会找，取最新的。

## Security / 安全

- `config.json` contains your API key and is excluded by `.gitignore`. Confirm the repo has no `config.json` before committing/pushing.
- `config.json` 含你的 API Key，已在 `.gitignore` 排除。提交/推送前请确认仓库里没有 `config.json`。
- The script never writes the key into logs or responses.
- 脚本不会把 Key 写进日志或响应。
- Images are sent to the vision endpoint over HTTPS, used only for this transcription, and are not persisted (pasted-image temp files are managed by the host environment).
- 图片通过 HTTPS 发给视觉模型端点，仅用于本次转述，不落盘（粘贴图片的临时文件由宿主环境管理）。

## FAQ / 常见问题

**"API key not configured" / 提示"未配置 API Key"**
Run `python describe_image.py --setup`, or set `DESCRIBE_IMAGE_API_KEY`.
先运行 `python describe_image.py --setup`，或设置 `DESCRIBE_IMAGE_API_KEY`。

**"No image found in transcripts / paste directory" / 提示"没在会话记录/粘贴目录中找到图片"**
You have not pasted an image, or it is not in a recent session. Pass an explicit path, or paste the image again and retry.
你还没贴图，或者图不在最近的会话里。直接传入图片路径，或重新粘贴后重试。

**`--test` fails / `--test` 失败**
Check that the Base URL ends with `/v1`, the model name is valid for your provider, the key has permission, and the network can reach the endpoint.
检查 Base URL 是否以 `/v1` 结尾、模型名是否对当前平台有效、Key 是否有权限、网络是否能连通该端点。

**The host model still does not auto-trigger / 宿主模型仍不自动触发转述**
Make sure `SKILL.md` is loaded with the skill directory; if the environment does not scan that directory, move it to the corresponding skills directory. You can also run the script manually in the conversation.
确认 `SKILL.md` 已随技能目录加载；若环境不扫描该目录，放到对应技能目录。也可以在对话里手动运行脚本。

## Development & contributing / 开发与贡献

- Zero third-party dependencies; all logic lives in the single file `describe_image.py`.
- 脚本零第三方依赖，逻辑在 `describe_image.py` 单文件内。
- Self-test after changes: `python describe_image.py --test` and an explicit-path transcription.
- 改动后自测：`python describe_image.py --test` 和显式路径转述。
- Never commit `config.json`.
- 提交时不要带上 `config.json`。
- Issues / PRs that add new provider presets are welcome.
- 欢迎提 issue / PR 补充新的平台预设。

## License / 许可

[MIT](LICENSE)
