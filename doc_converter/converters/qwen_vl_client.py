"""DashScope OpenAI 兼容接口的最小封装。

只用于 OCR/表格识别场景：把图片 base64 编码后发给 Qwen-VL-Plus，
按预定义 prompt 让模型返回结构化 JSON。

设计原则：
- 不引入新依赖（只用标准库 + httpx 或 urllib）。
- 依赖外部注入 base_url / api_key / model，避免与项目配置耦合。
- 失败时抛 ``QwenVlError``，由调用方决定是否回退到本地 Tesseract。
"""

from __future__ import annotations

import base64
import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

_log = logging.getLogger("doc_converter.qwen_vl")


class QwenVlError(RuntimeError):
    """Qwen-VL 调用失败。"""


@dataclass
class QwenVlConfig:
    """调用 Qwen-VL 所需的最小配置。"""

    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-vl-plus"
    timeout: int = 60


# ---------------------------------------------------------------------- #
# 图片编码
# ---------------------------------------------------------------------- #
def encode_image_as_data_url(path: str, mime_hint: Optional[str] = None) -> str:
    """把图片文件读成 ``data:<mime>;base64,...`` 字符串。

    Args:
        path: 本地图片路径。
        mime_hint: 可选 MIME 提示；缺省时按扩展名推断。

    Returns:
        完整的 data URL 字符串，可直接放入 OpenAI ``image_url`` 字段。
    """
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        raise QwenVlError(f"图片文件不存在: {p}")

    suffix = p.suffix.lower()
    if mime_hint:
        mime = mime_hint
    else:
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".webp": "image/webp",
        }.get(suffix, "image/png")

    raw = p.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------------- #
# Prompt
# ---------------------------------------------------------------------- #
TABLE_PROMPT = """你是一个专业的表格识别助手。请仔细查看用户上传的图片，识别其中所有的表格内容，并按以下规则输出严格的 JSON：

# 输出 JSON schema（不要包含任何额外字段、不要包含 markdown 代码块）
{
  "has_table": true,
  "header": [["单元格内容", "单元格内容", ...], ...],   // 二维数组：表头所有行
  "rows":   [["单元格内容", "单元格内容", ...], ...],   // 二维数组：数据行
  "merges": [{"r1":0,"c1":0,"r2":0,"c2":3,"value":"类别"}, ...]
}

# 最重要的规则 —— 表头列数与数据列数必须严格一致
- **整张表的总列数 = N**（数一下图片里有几条竖直分隔线/几条独立的纵向格子）。
- 表头每一行 `header[i]` 必须是长度为 N 的数组（每一列一个值；空格子用 "" 表示）。
- 数据每一行 `rows[i]` 必须是长度为 N 的数组。
- 横向合并的单元格（占多列）：**每个被占用的列都要写完整字符串**，不能省略。
- 纵向合并的单元格（占多行）：**每一行都写完整字符串**，不能省略。
- 缺失或无意义的格子（合并区被覆盖的位置）写 ""，**不要**输出 null。

# merges 字段
- `r1` / `c1` / `r2` / `c2`：0-based 行列号（含端点）。
- 列出每个**视觉上合并的区域**，含值 `value`。
- 同一合并区域只输出一次，**不要重复**。
- 没有合并时 `merges` 输出 []。

# 合并单元格识别要点（务必仔细看图）
- 表头常常是 2-3 行，最顶行可能跨多列（如"类别"占 4 列），下一行再细分。
- 每一行表头都要独立判断合并范围，不能用一行推断所有行。
- 第一列标签（如"批次"）可能跨所有表头行；数据行中只有一行（如"一本"），不要把它当合并。

# 其它
- 数字保留原始阿拉伯数字，不要加千分位/单位。
- 如果图片中无表格，把 `has_table` 设为 false。
- 只输出合法 JSON，禁止解释性文字，禁止 markdown 围栏。"""


# ---------------------------------------------------------------------- #
# 调用
# ---------------------------------------------------------------------- #
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    """从模型回复中提取 JSON 对象。

    模型有时会输出多余的 ```json``` 包裹或前后缀说明，需做容错。
    """
    if not raw or not raw.strip():
        raise QwenVlError("模型返回为空")

    # 1) 尝试直接 parse
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 2) 去掉 markdown 围栏再 parse
    m = _JSON_FENCE_RE.search(raw)
    if m:
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # 3) 抓取最外层 {...}
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        snippet = raw[start : end + 1]
        try:
            obj = json.loads(snippet)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError as exc:
            raise QwenVlError(f"无法解析模型返回的 JSON: {exc}; 原文前 200 字: {raw[:200]}") from exc

    raise QwenVlError(f"模型返回不含合法 JSON: {raw[:200]}")


def _do_http_request(url: str, payload: dict, cfg: QwenVlConfig, image_path: str) -> dict:
    """发送 HTTP 请求并返回解析后的 JSON envelope。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    _log.info("调用 Qwen-VL: model=%s, image=%s, url=%s", cfg.model, image_path, url)
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        raise QwenVlError(
            f"Qwen-VL HTTP {exc.code}: {exc.reason}; body={err_body[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise QwenVlError(f"调用 Qwen-VL 网络失败: {exc.reason}") from exc
    except TimeoutError as exc:
        raise QwenVlError(f"调用 Qwen-VL 超时（>{cfg.timeout}s）") from exc

    if status != 200:
        raise QwenVlError(f"Qwen-VL HTTP {status}: {raw[:500]}")

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QwenVlError(f"Qwen-VL 返回非 JSON: {raw[:200]}") from exc

    return envelope


def _extract_choices_content(envelope: dict) -> str:
    """从 OpenAI 兼容格式的 envelope 中提取文本内容。

    支持两种 content 形态：
    - 纯字符串（OpenAI 兼容）
    - list[dict]（DashScope 原生多模态）
    """
    try:
        content = envelope["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise QwenVlError(f"Qwen-VL 返回结构异常: {envelope}") from exc

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                # DashScope 原生格式: {"text": "..."}
                if "text" in item:
                    text_parts.append(str(item["text"]))
                # OpenAI 兼容 list 格式: {"type":"text","text":"..."}
                elif item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
        return "\n".join(text_parts)

    raise QwenVlError(f"Qwen-VL content 无法解析: {type(content).__name__}")


def _try_chat_openai_compatible(cfg: QwenVlConfig, image_path: str, prompt: str, max_tokens: int) -> dict:
    """OpenAI 兼容模式：POST /chat/completions，同时尝试 DashScope 原生和多模态端点。"""
    data_url = encode_image_as_data_url(image_path)

    # ---- 策略 1：OpenAI 兼容格式 ----
    url = cfg.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": max_tokens,
    }
    envelope = _do_http_request(url, payload, cfg, image_path)

    # 如果返回了 choices，直接用
    if "choices" in envelope:
        return _extract_json(_extract_choices_content(envelope))

    _log.warning("OpenAI 兼容模式返回无 choices，尝试 DashScope 原生格式: %s",
                 {k: v for k, v in envelope.items() if k in ("status_message", "status_name", "code", "message")})

    # ---- 策略 2：DashScope 原生多模态格式 ----
    native_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    native_payload = {
        "model": cfg.model,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": data_url},
                        {"text": prompt},
                    ],
                }
            ]
        },
        "parameters": {
            "max_tokens": max_tokens,
        },
    }
    envelope2 = _do_http_request(native_url, native_payload, cfg, image_path)

    # 原生 API 返回格式: {"output": {"choices": [...]}}
    if "output" in envelope2 and "choices" in envelope2["output"]:
        content = envelope2["output"]["choices"][0]["message"]["content"]
        if isinstance(content, list):
            text_parts = [str(item["text"]) for item in content if isinstance(item, dict) and "text" in item]
            content = "\n".join(text_parts)
        if isinstance(content, str):
            return _extract_json(content)

    raise QwenVlError(f"Qwen-VL 原生 API 返回结构异常: {envelope2}")


def chat_with_image(
    *,
    cfg: QwenVlConfig,
    image_path: str,
    prompt: str = TABLE_PROMPT,
    max_tokens: int = 4096,
) -> dict:
    """调用 Qwen-VL 视觉模型，返回解析后的 JSON dict。

    自动尝试多种 API 格式（按顺序）：
    1. OpenAI 兼容格式（/chat/completions）
    2. DashScope 原生多模态格式（multimodal-generation）

    Raises:
        QwenVlError: 所有格式均失败。
    """
    if not cfg.api_key:
        raise QwenVlError("未配置 Qwen API Key（QWEN_API_KEY 为空）")

    return _try_chat_openai_compatible(cfg, image_path, prompt, max_tokens)