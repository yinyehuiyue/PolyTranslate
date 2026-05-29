# -*- coding: utf-8 -*-
"""
================================================================================
 游戏文本翻译核心模块 (Model 层)
================================================================================
 职责：
   1. 封装 DeepSeek API（兼容 OpenAI 格式）调用逻辑
   2. 构建包含术语表的 System Prompt
   3. 配置文件的加密存储与读取（API Key 本地混淆保存）
   4. 网络重试与乱码检测机制
================================================================================
"""

import json
import os
import base64
import re
import time
from threading import Lock
from openai import OpenAI

# ==================== 常量定义 ====================

# 配置文件路径（与脚本同目录）
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# 术语字典路径（用户手动放置）
DICT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dict.json")

# 异或混淆密钥（本地级防护，防止明文泄露 API Key）
_XOR_KEY = b"Gam3L0cal1zer_2024_SecureKey!@#"  # 固定混淆密钥，请勿修改

# 最大重试次数
MAX_RETRIES = 3

# API 请求超时时间（秒）
API_TIMEOUT = 30


# ==================== System Prompt ====================

SYSTEM_PROMPT_BASE = """你是一位拥有10年经验的资深游戏本地化专家。
你的任务是将用户提供的游戏文本原汁原味地翻译为简体中文。

【翻译铁律 - 必须严格遵守】
1. 变量占位符保护：所有 {}、%d、%s、%f、{0}、{name} 等格式的占位符必须原样保留，不得翻译或修改。
2. 转义字符保护：所有 \\n（换行）、\\t（制表符）、\\r 等转义字符必须原样保留。
3. 颜色/富文本标签保护：所有 <color=...>、</color>、<size=...>、<b>、</b>、<i>、</i> 等 XML/HTML 标签必须原样保留。
4. 格式保护：原文中的标点符号风格、特殊符号（如 ★、☆、→ 等）可根据中文习惯适当调整，但不能丢失信息。
5. 输出格式：仅输出翻译后的中文文本，绝对不要附加任何解释、注释或问候语。
6. 游戏感：翻译要符合游戏语境，用词自然生动，符合角色身份和场景氛围。

【术语表】
以下术语翻译为强制标准，翻译时必须严格遵循：
{TERM_GLOSSARY}

请开始翻译。"""


# ==================== 配置管理器 ====================

class ConfigManager:
    """
    配置管理器
    负责 config.json 的读写，以及 API Key 的混淆/解混淆。
    """

    # 类级锁，防止并发读写配置
    _lock = Lock()

    @staticmethod
    def _xor_obfuscate(data: bytes) -> bytes:
        """
        异或混淆算法：将数据与固定密钥进行异或运算。
        同一算法用于加密和解密（对称运算）。

        参数:
            data: 原始字节数据
        返回:
            混淆后的字节数据
        """
        key = _XOR_KEY
        key_len = len(key)
        return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))

    @classmethod
    def encrypt_api_key(cls, plain_text: str) -> str:
        """
        将明文 API Key 加密为 base64 字符串。

        流程: 明文 → UTF-8 编码 → 异或混淆 → Base64 编码
        """
        if not plain_text:
            return ""
        raw_bytes = plain_text.encode("utf-8")
        obfuscated = cls._xor_obfuscate(raw_bytes)
        return base64.b64encode(obfuscated).decode("utf-8")

    @classmethod
    def decrypt_api_key(cls, encrypted_text: str) -> str:
        """
        将加密后的 base64 字符串还原为明文 API Key。

        流程: Base64 解码 → 异或去混淆 → UTF-8 解码
        """
        if not encrypted_text:
            return ""
        try:
            obfuscated = base64.b64decode(encrypted_text.encode("utf-8"))
            raw_bytes = cls._xor_obfuscate(obfuscated)
            return raw_bytes.decode("utf-8")
        except Exception:
            # 如果解密失败（比如密钥不匹配或数据损坏），返回空字符串
            return ""

    @classmethod
    def load_config(cls) -> dict:
        """
        从 config.json 加载配置，并自动解密 API Key。

        如果配置文件不存在，返回默认空配置。
        如果加密的 API Key 存在，解密后放回字典。

        返回:
            包含 api_key(明文), base_url, model_name 的字典
        """
        with cls._lock:
            default_config = {
                "api_key": "",      # 明文（内存中使用）
                "base_url": "https://api.deepseek.com",
                "model_name": "deepseek-chat",
                # 内部存储用的加密字段名
                "api_key_encrypted": ""
            }

            if not os.path.exists(CONFIG_PATH):
                return default_config

            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, IOError):
                return default_config

            # 解密 API Key
            encrypted = raw.get("api_key_encrypted", "")
            if encrypted:
                raw["api_key"] = cls.decrypt_api_key(encrypted)
            else:
                # 兼容旧版明文存储（如果存在）
                raw["api_key"] = raw.get("api_key", "")

            # 确保必要字段存在
            raw.setdefault("base_url", "https://api.deepseek.com")
            raw.setdefault("model_name", "deepseek-chat")

            return raw

    @classmethod
    def save_config(cls, api_key_plain: str, base_url: str, model_name: str) -> bool:
        """
        保存配置到 config.json。

        参数:
            api_key_plain: 明文 API Key
            base_url: API 基础地址
            model_name: 模型名称
        返回:
            是否保存成功
        """
        with cls._lock:
            config = {
                "api_key_encrypted": cls.encrypt_api_key(api_key_plain),
                "base_url": base_url.strip() or "https://api.deepseek.com",
                "model_name": model_name.strip() or "deepseek-chat"
            }
            try:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                return True
            except IOError:
                return False


# ==================== 术语管理器 ====================

class GlossaryManager:
    """
    术语表管理器
    负责加载用户提供的 dict.json 术语字典文件。
    """

    @staticmethod
    def load_glossary() -> dict:
        """
        加载本地术语字典。

        返回:
            术语字典（key=源语言, value=目标语言），文件不存在时返回空字典
        """
        if not os.path.exists(DICT_PATH):
            return {}
        try:
            with open(DICT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except (json.JSONDecodeError, IOError):
            return {}

    @staticmethod
    def format_glossary_for_prompt(glossary: dict) -> str:
        """
        将术语字典格式化为可注入 System Prompt 的字符串。

        参数:
            glossary: 术语字典
        返回:
            格式化的术语表文本，如 "Elixir → 灵药\nGoblin → 哥布林"
        """
        if not glossary:
            return "（未加载术语表）"
        lines = [f"  {src} → {tgt}" for src, tgt in glossary.items()]
        return "\n".join(lines)


# ==================== 翻译引擎 ====================

class TranslationEngine:
    """
    游戏文本翻译引擎
    封装 OpenAI 兼容 API 的调用流程，包含重试与乱码检测。
    """

    def __init__(self, api_key: str, base_url: str, model_name: str):
        """
        初始化翻译引擎。

        参数:
            api_key: 明文 API Key
            base_url: API 基础地址（如 https://api.deepseek.com）
            model_name: 模型名称（如 deepseek-chat）
        """
        self._api_key = api_key
        self._base_url = base_url
        self._model_name = model_name
        self._client = None
        self._build_client()

    def _build_client(self):
        """
        构建 OpenAI 客户端实例。
        如果 API Key 为空则不创建客户端。
        """
        if self._api_key:
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url
            )
        else:
            self._client = None

    def update_credentials(self, api_key: str, base_url: str, model_name: str):
        """
        更新 API 凭证并重建客户端。

        参数:
            api_key: 新的明文 API Key
            base_url: 新的 Base URL
            model_name: 新的模型名称
        """
        self._api_key = api_key
        self._base_url = base_url
        self._model_name = model_name
        self._build_client()

    @staticmethod
    def _has_repeating_garbage(text: str, threshold: int = 8) -> bool:
        """
        检测文本中是否存在连续重复字符（判定为乱码/幻觉输出）。

        检测逻辑：寻找同一个字符连续出现 threshold 次及以上的情况。
        例如 "啊啊啊啊啊啊啊啊" 会被检测为乱码。

        参数:
            text: 待检测文本
            threshold: 重复字符阈值（默认 8）
        返回:
            True 表示检测到乱码
        """
        if not text:
            return False
        # 匹配任意单个字符连续出现 threshold 次及以上
        pattern = re.compile(r"(.)\1{" + str(threshold - 1) + r",}")
        return bool(pattern.search(text))

    def _build_system_prompt(self) -> str:
        """
        动态构建完整的 System Prompt（含术语表注入）。

        返回:
            包含术语表的完整 System Prompt
        """
        glossary = GlossaryManager.load_glossary()
        glossary_text = GlossaryManager.format_glossary_for_prompt(glossary)
        return SYSTEM_PROMPT_BASE.replace("{TERM_GLOSSARY}", glossary_text)

    def translate(self, source_text: str) -> tuple[str, str]:
        """
        执行翻译（带重试机制）。

        参数:
            source_text: 待翻译的原文
        返回:
            (状态, 翻译结果)
            - 状态 "ok": 翻译成功，result 为译文
            - 状态 "error": 翻译失败，result 为错误信息
        """
        if not self._client:
            return ("error", "❌ 请先在设置中配置 API Key、Base URL 和模型名称。")

        if not source_text.strip():
            return ("error", "❌ 请输入待翻译的文本。")

        system_prompt = self._build_system_prompt()

        last_error = ""

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # 调用 OpenAI 兼容 API（流式=False，一次性返回）
                response = self._client.chat.completions.create(
                    model=self._model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": source_text}
                    ],
                    temperature=0.3,       # 低温度，提高翻译稳定性
                    max_tokens=4096,
                    timeout=API_TIMEOUT
                )

                # 提取翻译结果
                result_text = response.choices[0].message.content

                if result_text is None:
                    last_error = "API 返回了空内容"
                    if attempt < MAX_RETRIES:
                        time.sleep(attempt)  # 递增等待
                        continue
                    return ("error", f"❌ {last_error}（已重试{MAX_RETRIES}次）")

                result_text = result_text.strip()

                # 乱码检测
                if self._has_repeating_garbage(result_text):
                    last_error = "检测到乱码/重复字符"
                    if attempt < MAX_RETRIES:
                        time.sleep(attempt)
                        continue
                    return ("error", f"❌ {last_error}（已重试{MAX_RETRIES}次）")

                # 成功
                return ("ok", result_text)

            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    time.sleep(attempt)  # 递增等待后重试
                    continue
                # 最后一次也失败了
                return ("error", f"❌ 翻译失败: {last_error}（已重试{MAX_RETRIES}次）")

        return ("error", f"❌ 未知错误（已重试{MAX_RETRIES}次）")


# ==================== 模块自检 ====================

if __name__ == "__main__":
    # 简单自检：打印配置路径和术语表
    print(f"配置文件路径: {CONFIG_PATH}")
    print(f"术语字典路径: {DICT_PATH}")

    cfg = ConfigManager.load_config()
    print(f"当前配置: base_url={cfg['base_url']}, model={cfg['model_name']}")
    print(f"API Key 已配置: {'是' if cfg['api_key'] else '否'}")

    glossary = GlossaryManager.load_glossary()
    print(f"术语表条目数: {len(glossary)}")
    if glossary:
        print("术语表内容:")
        for k, v in glossary.items():
            print(f"  {k} → {v}")