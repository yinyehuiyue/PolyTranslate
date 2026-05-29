# -*- coding: utf-8 -*-
"""
================================================================================
 配置管理器
================================================================================
 负责 config.json 的读写、API Key 混淆/解混淆、配置校验。
 v3.0 升级: 新增 custom_prompt, style_preset, glossary_entries 字段。
================================================================================
"""

import json
import os
import base64
from threading import Lock

# 配置文件路径（与 main.py 同目录）
_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"
)

# 异或混淆密钥
_XOR_KEY = b"Gam3L0cal1zer_2024_SecureKey!@#"


class ConfigManager:
    """配置管理器（纯静态方法）"""

    _lock = Lock()

    # ── 提供商预设 (20+ 厂商，兼容 OpenAI 格式) ──
    PROVIDER_PRESETS = {
        # 国际巨头
        "OpenAI (GPT-4o)":       ("https://api.openai.com/v1", "gpt-4o"),
        "Google Gemini":         ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.0-flash"),
        "Anthropic Claude":      ("https://api.anthropic.com/v1", "claude-3-opus-20240229"),
        "Azure OpenAI":           ("https://YOUR-RESOURCE.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT", "gpt-4o"),
        "Groq":                  ("https://api.groq.com/openai/v1", "llama3-70b-8192"),
        "Together AI":           ("https://api.together.xyz/v1", "meta-llama/Llama-3-70b"),
        # 国内头部
        "百度文心 (Ernie)":       ("https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat", "ernie-4.0"),
        "阿里通义 (Qwen)":        ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-max"),
        "腾讯混元 (Hunyuan)":     ("https://api.hunyuan.cloud.tencent.com/v1", "hunyuan-pro"),
        "智谱 ChatGLM":           ("https://open.bigmodel.cn/api/paas/v4", "glm-4"),
        "月之暗面 Kimi":          ("https://api.moonshot.cn/v1", "moonshot-v1-8k"),
        "零一万物 Yi":            ("https://api.lingyiwanwu.com/v1", "yi-large"),
        "阶跃星辰 StepFun":       ("https://api.stepfun.com/v1", "step-1-8k"),
        "MiniMax":               ("https://api.minimax.chat/v1", "abab6.5s-chat"),
        # 开源与聚合
        "DeepSeek":              ("https://api.deepseek.com", "deepseek-chat"),
        "硅基流动 SiliconFlow":    ("https://api.siliconflow.cn/v1", "Qwen/Qwen2.5-7B-Instruct"),
        "OneAPI 聚合中转":         ("https://your-oneapi-instance.com/v1", "gpt-3.5-turbo"),
        "OpenRouter":             ("https://openrouter.ai/api/v1", "openai/gpt-4o"),
        # 本地离线
        "Ollama (本地离线)":       ("http://localhost:11434/v1", ""),
        "LM Studio (本地离线)":    ("http://localhost:1234/v1", ""),
        "vLLM (本地离线)":         ("http://localhost:8000/v1", ""),
        # 自定义
        "OpenAI 兼容 (自定义)":    ("", ""),
    }

    # ── 常用模型列表 (Editable Combobox) ──
    MODEL_OPTIONS = [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
        "deepseek-chat", "deepseek-reasoner",
        "qwen3", "qwen3-14b", "qwen3-32b", "hy-mt1.5-1.8b",
        "llama3", "llama3.1", "mistral", "mixtral",
        "gemma3", "command-r", "claude-3-opus",
    ]

    # ---------- 混淆算法 ----------

    @staticmethod
    def _xor_obfuscate(data: bytes) -> bytes:
        key = _XOR_KEY
        key_len = len(key)
        return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))

    @classmethod
    def encrypt(cls, plain: str) -> str:
        if not plain:
            return ""
        return base64.b64encode(
            cls._xor_obfuscate(plain.encode("utf-8"))
        ).decode("utf-8")

    @classmethod
    def decrypt(cls, encrypted: str) -> str:
        if not encrypted:
            return ""
        try:
            return cls._xor_obfuscate(
                base64.b64decode(encrypted.encode("utf-8"))
            ).decode("utf-8")
        except Exception:
            return ""

    # ---------- 配置加载 / 保存 ----------

    @classmethod
    def default_config(cls) -> dict:
        """返回默认配置模板"""
        return {
            # API 配置
            "api_key": "",                   # 内存明文
            "api_key_encrypted": "",         # 磁盘密文
            "provider": "OpenAI 兼容 (万能)",  # 模型厂商
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o",
            # 翻译风格配置
            "style_preset": "无特定风格",
            "custom_prompt": "",
            # 术语字典内联存储
            "glossary_entries": {},          # {src: tgt}
            # 安全设置
            "safe_mode": False,               # True=禁用内存注入，仅文件注入
            # 应用元数据
            "first_run": True,
        }

    @classmethod
    def load(cls) -> dict:
        """
        加载配置。config.json 不存在则返回默认配置。
        API Key 自动解密到 api_key 字段。
        """
        with cls._lock:
            default = cls.default_config()
            if not os.path.exists(_CONFIG_PATH):
                return default
            try:
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, IOError):
                return default

            # 解密 API Key
            encrypted = raw.get("api_key_encrypted", "")
            raw["api_key"] = cls.decrypt(encrypted) if encrypted else raw.get("api_key", "")

            # 填充缺失字段
            for k, v in default.items():
                raw.setdefault(k, v)
            return raw

    @classmethod
    def save(cls, data: dict) -> bool:
        """
        保存配置。自动加密 api_key → api_key_encrypted。

        参数:
            data: 完整配置字典（含明文 api_key）
        返回:
            是否保存成功
        """
        with cls._lock:
            payload = dict(data)
            # 加密 API Key
            payload["api_key_encrypted"] = cls.encrypt(
                payload.pop("api_key", "")
            )
            # 移除内存中的明文（不写入磁盘）
            payload.pop("api_key", None)
            try:
                with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                return True
            except IOError:
                return False

    @classmethod
    def update_field(cls, key: str, value) -> bool:
        """更新单个配置字段并保存"""
        config = cls.load()
        config[key] = value
        return cls.save(config)