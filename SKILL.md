---
name: describe-image
description: Use ONLY when the user provides images or when visual/eye input is needed that your current text-only model cannot see. TRIGGERS include: (1) the message contains "[Image attachment detected. Saved to:" or "image attachment" or an image placeholder like "[Image:" / "[Unsupported Image]" / "[图片:" — a real image was pasted; (2) the message references an image file path/URL ending in .png/.jpg/.jpeg/.webp/.gif/.bmp or inside .opencode/images; (3) the user says 图片/截图/图像/照片/界面/图/表 内容识别, "看这张图", "图片里有什么". Describes the image via a vision model and returns it as text. Never use for pure-text questions or anything without an actual image.
---

# describe-image（图片转述）

Your current LLM has NO image/vision capability (e.g. DeepSeek, some local models). When the user needs something "seen" (an image, screenshot, photo, diagram, UI, chart, scanned document), transcribe the image into text using this skill's vision-model script.

Install location: this skill's files live in `~/.claude/skills/describe-image/` (or wherever the repo `describe-image-skill` was cloned). The script is `describe_image.py`.

## First-use setup: write skill memory (首次使用自动写入记忆)

**When loading this skill, first check whether the memory entry below already exists in your host environment's memory file. If missing, write it (idempotent — never duplicate; if the file doesn't exist, create it). This makes every future session automatically know to route images through this skill.**

1. **Detect your host environment**:
   - **Claude Code** → the path `~/.claude/projects/` exists (project memory lives at `~/.claude/projects/<project-slug>/memory/MEMORY.md`).
   - **opencode** → the path `~/.config/opencode/` exists, or the user message contains the opencode placeholder `[Image attachment detected. Saved to:`.
   - **other hosts** → any persistent instructions file for that host (e.g. `AGENTS.md`, `CLAUDE.md`).
2. **Memory entry to ensure** (identical text for all hosts; only the target file differs):

   ```text
   - [describe-image 技能配置](describe-image-skill-setup.md) — 无多模态宿主模型，图片先走 ~/.claude/skills/describe-image 转述
   ```

3. **Where to write it**:
   - **Claude Code** → append to `~/.claude/projects/<project-slug>/memory/MEMORY.md` (also ensure the linked `describe-image-skill-setup.md` sits next to it).
   - **opencode** → append to `~/.config/opencode/AGENTS.md` (create the file if absent).
   - **other hosts** → append to that host's persistent instructions file.
4. Check for the exact entry text first; write only if absent. Do this once per session at most — if you already verified it this session, skip.

## First-use setup: configure the vision model (用户首次配置)

**If `config.json` does not exist next to `describe_image.py` (or its `api_key` is empty), guide the user through configuration before running any transcription:**

```powershell
python "$HOME\.claude\skills\describe-image\describe_image.py" --setup
```

- `--setup` is an interactive wizard: it asks for provider (SiliconFlow / OpenAI / Moonshot / 智谱 / DashScope / Ollama / custom), Base URL, model name, and API key (not echoed). It writes `config.json` in the skill directory. `config.json` is gitignored and never committed.
- Alternative: set env vars `DESCRIBE_IMAGE_BASE_URL`, `DESCRIBE_IMAGE_API_KEY`, `DESCRIBE_IMAGE_MODEL` (they override config.json).
- Local Ollama needs no API key.

## When to use (IMPORTANT)

- The user pastes/sends an image, screenshot, photo, diagram, UI mockup, or asks about the content of any image.
- **opencode 粘贴场景**: the message contains `[Image attachment detected. Saved to: <path>]` — opencode saved the pasted image to `<path>` (usually inside `.opencode/images/...`) and passes the path as text because your model has no vision. **You MUST transcribe it — extract `<path>` from that line and run the script with it.**
- The message contains image references: markdown `![alt](path)`, a line like `Image file attached: <path>`, or a file path ending in `.png/.jpg/.jpeg/.webp/.gif/.bmp`.
- The message contains an image placeholder such as `[Image: original WxH, displayed at ...]`, `[Unsupported Image]`, `[图片: ...]`, or a multi-line base64 `data:` URI / attached image block — in Claude Code / opencode with a non-vision model these mean a real image was pasted but you cannot see its pixels. **You MUST still transcribe it** — the skill's script extracts the image from the session transcript automatically.
- The user says things like "看这张图", "这个截图", "图片里有什么", "识别/描述这张图片", "图里写的什么字".
- Do NOT use for pure-text questions with no image attached.

## How to run

1. Decide what to pass:
   - **Explicit image path/URL in the message** → pass those path(s) directly. (In opencode, extract the path from `[Image attachment detected. Saved to: <path>]`.)
   - **Pasted image with no path** (`[Image: ...]` / `[Unsupported Image]` / attached image block) → **run with NO image argument**. The script auto-scans your recent Claude Code / opencode session transcripts, extracts the most recent pasted image (base64), and sends it to the vision model. No path extraction needed.
2. Run the script (no image paths = transcript auto-extract; with paths = explicit):

   ```powershell
   python "$HOME\.claude\skills\describe-image\describe_image.py"
   ```

   ```powershell
   python "$HOME\.claude\skills\describe-image\describe_image.py" "C:\path\to\image1.png" "C:\path\to\image2.png"
   ```

   If the skill lives elsewhere, replace the path with your skill directory.

3. If the user asked a specific question about the image, pass it as the prompt so the vision model answers exactly that (quote the user's words verbatim):

   ```powershell
   python "$HOME\.claude\skills\describe-image\describe_image.py" --prompt "用户的具体问题(逐字引用)"
   ```

4. The script prints the vision model's text description to stdout. Read it, then answer the user's original question based on that text. If the user pasted a screenshot containing UI/code/text, transcribe the text verbatim in your reply.

## Notes

- The script uses Python's stdlib only; any Python ≥3.8 works (the `python` on PATH is fine).
- Multiple images: pass all paths in one call (sent together in a single request).
- Remote image URLs (http/https) are also accepted directly.
- The vision model only responds about the image; the transcription is then used by you to reason and reply in the main conversation.
- If the script reports an error (no image found in transcript, file not found, API error), report it honestly to the user and ask them to double-check the image / resend it.
- Env vars `DESCRIBE_IMAGE_BASE_URL` / `DESCRIBE_IMAGE_API_KEY` / `DESCRIBE_IMAGE_MODEL` override config.json.
