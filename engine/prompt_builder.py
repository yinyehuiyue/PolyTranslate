# -*- coding: utf-8 -*-
"""
================================================================================
 动态提示词构建器
================================================================================
 职责:
   1. 提供多套风格预设模板
   2. 动态注入术语表 + 自定义提示词
   3. 按优先级拼接最终 System Prompt
================================================================================
"""

# ==================== 风格预设库 ====================

STYLE_PRESETS = {
    "无特定风格": "",
    "二次元轻小说风": (
        "【风格指令】\n"
        "采用轻松活泼的二次元轻小说风格，语气可爱灵动。\n"
        "适度使用「～」「呢」「嘛」「呀」等语气词。\n"
        "角色对话要有鲜明的个性与情感色彩，让读者感受到角色的魅力。"
    ),
    "硬核科幻风": (
        "【风格指令】\n"
        "采用冷峻精准的硬核科幻风格，术语翻译专业严谨。\n"
        "避免口语化表达，保持技术描述的准确性和严肃感。\n"
        "装备、科技名词优先选用有科技感的译名。"
    ),
    "信达雅文学风": (
        "【风格指令】\n"
        "遵循'信达雅'的翻译原则，在准确传达原文的基础上，追求文雅优美的中文表达。\n"
        "适当使用四字成语和文学修辞，但不可过度堆砌辞藻。\n"
        "保持原文的情感基调和叙事节奏。"
    ),
    "热血少年漫风": (
        "【风格指令】\n"
        "采用热血激昂的少年漫画风格，语气充满力量感和爆发力。\n"
        "招式名、技能名要有冲击力和记忆点。\n"
        "对话简洁有力，战斗场景要给人热血沸腾的感觉。"
    ),
    "严肃正剧风": (
        "【风格指令】\n"
        "采用严肃正剧风格，语气庄重沉稳。\n"
        "避免轻浮的网络用语和过度口语化。\n"
        "保持原文的历史厚重感和史诗气质。"
    ),
}

# ==================== 基础 System Prompt ====================

SYSTEM_PROMPT_BASE = """你是一位拥有10年经验的资深游戏本地化专家。
你的任务是将用户提供的游戏文本原汁原味地翻译为简体中文。

【翻译铁律 - 必须严格遵守】
1. 变量占位符保护：所有 {{}}、%d、%s、%f、{{0}}、{{name}} 等格式的占位符必须原样保留，不得翻译或修改。
2. 转义字符保护：所有 \\n（换行）、\\t（制表符）、\\r 等转义字符必须原样保留。
3. 颜色/富文本标签保护：所有 <color=...>、</color>、<size=...>、<b>、</b>、<i>、</i> 等 XML/HTML 标签必须原样保留。
4. 格式保护：原文中的标点符号风格、特殊符号（如 ★、☆、→ 等）可根据中文习惯适当调整，但不能丢失信息。
5. 输出格式：仅输出翻译后的中文文本，绝对不要附加任何解释、注释或问候语。
6. 游戏感：翻译要符合游戏语境，用词自然生动，符合角色身份和场景氛围。

{STYLE_INSTRUCTION}

【术语表】
以下术语翻译为强制标准，翻译时必须严格遵循：
{TERM_GLOSSARY}

{CUSTOM_INSTRUCTION}

请开始翻译。"""


# ==================== 构建器 ====================

class PromptBuilder:
    """
    动态提示词构建器。

    拼接顺序（优先级从低到高）:
      1. 基础角色设定 + 翻译铁律
      2. 风格预设指令
      3. 术语表
      4. 用户自定义提示词（最高优先级）
    """

    @staticmethod
    def get_style_names() -> list:
        """返回所有可用风格名称列表"""
        return list(STYLE_PRESETS.keys())

    @staticmethod
    def format_glossary(glossary: dict) -> str:
        """
        格式化术语表为可注入的文本。

        参数:
            glossary: {src: tgt} 术语字典
        返回:
            格式化字符串，如 "  Elixir → 灵药\n  Goblin → 哥布林"
        """
        if not glossary:
            return "（未加载术语表）"
        lines = [f"  {src} → {tgt}" for src, tgt in glossary.items()]
        return "\n".join(lines)

    @classmethod
    def build(
        cls,
        style: str = "无特定风格",
        glossary: dict = None,
        custom_prompt: str = "",
    ) -> str:
        """
        构建完整的 System Prompt。

        参数:
            style: 风格预设名称
            glossary: 术语字典
            custom_prompt: 用户自定义提示词
        返回:
            完整的 System Prompt 字符串
        """
        glossary = glossary or {}

        # 获取风格指令
        style_instruction = STYLE_PRESETS.get(style, "")
        if style_instruction:
            style_instruction = style_instruction + "\n"

        # 格式化术语表
        glossary_text = cls.format_glossary(glossary)

        # 格式化自定义指令
        custom_instruction = ""
        if custom_prompt.strip():
            custom_instruction = (
                "【用户特别要求 - 最高优先级】\n"
                "以下要求必须无条件遵守，优先级高于上述所有规则：\n"
                f"{custom_prompt.strip()}\n"
            )

        prompt = SYSTEM_PROMPT_BASE
        prompt = prompt.replace("{STYLE_INSTRUCTION}", style_instruction)
        prompt = prompt.replace("{TERM_GLOSSARY}", glossary_text)
        prompt = prompt.replace("{CUSTOM_INSTRUCTION}", custom_instruction)
        return prompt
