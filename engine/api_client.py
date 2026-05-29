# -*- coding: utf-8 -*-
"""
================================================================================
 统一 API 调度器
================================================================================
 核心设计:
   1. 只依赖 openai SDK（行业标准 OpenAI 兼容协议）
   2. API Key 非必填 — 本地模型自动填入 "not-needed"
   3. Base URL 智能补全（自动添加 http:// 和 /v1 后缀）
   4. 统一重试 + 乱码检测 + 占位符验证
================================================================================
"""

import time
from openai import OpenAI
from engine.config_manager import ConfigManager
from engine.prompt_builder import PromptBuilder
from utils.text_guard import TextGuard

# API 请求超时
API_TIMEOUT = 60
# 最大重试次数
MAX_RETRIES = 3


class UnifiedAPIClient:
    """
    统一 API 调度器。

    兼容所有 OpenAI Chat Completions 格式的服务:
      - 云端: DeepSeek, OpenAI, OpenRouter 等
      - 本地: LM Studio (localhost:1234/v1), Ollama (localhost:11434/v1), vLLM 等
    """

    def __init__(self, config: dict):
        """
        参数:
            config: ConfigManager.load() 返回的配置字典
        """
        self._config = config
        self._client = None
        self._build_client()

    # ---------- Base URL 智能补全 ----------

    @staticmethod
    def sanitize_base_url(url: str) -> str:
        """
        智能补全 Base URL:

        localhost:1234       →  http://localhost:1234/v1
        127.0.0.1:11434      →  http://127.0.0.1:11434/v1
        api.deepseek.com     →  https://api.deepseek.com/v1
        """
        url = url.strip().rstrip("/")
        if not url:
            return "http://localhost:11434/v1"  # 默认 Ollama
        # 补全协议
        if not url.startswith("http"):
            url = "http://" + url
        # 补全 /v1 后缀（避免重复追加）
        if "/v1" not in url:
            url += "/v1"
        return url

    # ---------- 客户端构建 ----------

    def _build_client(self):
        """构建（或重建）OpenAI 客户端实例"""
        base_url = self.sanitize_base_url(
            self._config.get("base_url", "")
        )
        api_key = self._config.get("api_key", "").strip()

        # ★ 关键: API Key 非必填。本地模型传占位符 "not-needed"
        if not api_key:
            api_key = "not-needed"

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=API_TIMEOUT,
        )
        self._base_url = base_url
        self._model = self._config.get("model_name", "deepseek-chat")

    def update_config(self, config: dict):
        """更新配置并重建客户端"""
        self._config = config
        self._build_client()

    # ---------- 单条翻译 ----------

    def translate_single(
        self, source_text: str, prompt_builder: PromptBuilder = None
    ) -> tuple:
        """
        翻译单条文本（带 3 次重试 + 乱码/占位符验证）。

        参数:
            source_text: 待翻译原文
            prompt_builder: PromptBuilder 实例（若为 None 则使用默认配置）
        返回:
            (status, result)
            - status="ok": result 为译文
            - status="error": result 为错误信息
        """
        if not source_text or not source_text.strip():
            return ("error", "❌ 文本为空")

        if prompt_builder is None:
            # 使用默认配置构建
            prompt_builder = PromptBuilder()
            glossary = self._config.get("glossary_entries", {})
            system_prompt = prompt_builder.build(
                style=self._config.get("style_preset", "无特定风格"),
                glossary=glossary,
                custom_prompt=self._config.get("custom_prompt", ""),
            )
        else:
            glossary = self._config.get("glossary_entries", {})
            system_prompt = prompt_builder.build(
                style=self._config.get("style_preset", "无特定风格"),
                glossary=glossary,
                custom_prompt=self._config.get("custom_prompt", ""),
            )

        last_error = ""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": source_text},
                    ],
                    temperature=0.3,
                    max_tokens=4096,
                )
                result_text = response.choices[0].message.content

                if result_text is None:
                    last_error = "API 返回了空内容"
                    if attempt < MAX_RETRIES:
                        time.sleep(attempt)
                        continue
                    return ("error", f"❌ {last_error}（已重试{MAX_RETRIES}次）")

                result_text = result_text.strip()

                # 乱码检测
                if TextGuard.has_repeating_garbage(result_text):
                    last_error = "检测到乱码/重复字符"
                    if attempt < MAX_RETRIES:
                        time.sleep(attempt)
                        continue
                    return ("error", f"❌ {last_error}（已重试{MAX_RETRIES}次）")

                # 占位符验证（非致命，仅日志）
                missing = TextGuard.validate_placeholders(source_text, result_text)
                # 不阻断翻译，但返回警告信息（在批量翻译中可忽略）

                return ("ok", result_text)

            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    time.sleep(attempt)
                    continue
                return (
                    "error",
                    f"❌ 翻译失败: {last_error}（已重试{MAX_RETRIES}次）",
                )

        return ("error", f"❌ 未知错误（已重试{MAX_RETRIES}次）")

    # ---------- 批量翻译（供提取器使用） ----------

    def translate_batch(
        self,
        entries: list,
        progress_callback=None,
    ) -> int:
        """
        批量翻译一组 TextEntry。

        参数:
            entries: TextEntry 对象列表（需有 source_text, translated_text 属性）
            progress_callback: callable(idx, total, status_text) — 进度回调
        返回:
            成功翻译的数量
        """
        total = len(entries)
        success_count = 0
        for i, entry in enumerate(entries):
            if progress_callback:
                progress_callback(
                    i + 1, total, f"正在翻译 {i + 1}/{total}..."
                )
            status, result = self.translate_single(entry.source_text)
            if status == "ok":
                entry.translated_text = result
                success_count += 1
            else:
                entry.translated_text = f"[翻译失败] {result}"
        return success_count