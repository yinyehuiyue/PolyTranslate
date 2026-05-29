# -*- coding: utf-8 -*-
"""
================================================================================
 端到端功能测试脚本
================================================================================
 运行方式: python test_e2e.py
 验证: 配置读写、API 客户端、翻译流程、注入流程 (不实际调用 API)
================================================================================
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """测试 1: 配置读写与加密"""
    from engine.config_manager import ConfigManager
    config = ConfigManager.load()
    assert "api_key" in config, "api_key 字段缺失"
    assert "base_url" in config, "base_url 字段缺失"
    assert "model_name" in config, "model_name 字段缺失"
    assert "provider" in config, "provider 字段缺失"

    # 测试加密/解密
    plain = "sk-test-key-12345"
    encrypted = ConfigManager.encrypt(plain)
    decrypted = ConfigManager.decrypt(encrypted)
    assert decrypted == plain, f"加密/解密失败: {decrypted} != {plain}"

    # 测试保存/加载
    config["api_key"] = plain
    assert ConfigManager.save(config), "保存配置失败"
    loaded = ConfigManager.load()
    assert loaded["api_key"] == plain, "加载后 API Key 不匹配"

    # 测试厂商预设
    assert "OpenAI 兼容 (万能)" in ConfigManager.PROVIDER_PRESETS
    assert "Ollama (本地)" in ConfigManager.PROVIDER_PRESETS
    assert len(ConfigManager.MODEL_OPTIONS) >= 10, "模型列表不足"

    print("[PASS] 测试 1: 配置读写与加密")


def test_api_client():
    """测试 2: API 客户端与 URL 补全"""
    from engine.api_client import UnifiedAPIClient
    from engine.config_manager import ConfigManager

    config = ConfigManager.load()
    client = UnifiedAPIClient(config)

    # 测试 sanitize_base_url
    assert "/v1" in client.sanitize_base_url("api.deepseek.com"), "需补全 /v1"
    assert client.sanitize_base_url("https://api.openai.com/v1") == "https://api.openai.com/v1", "不应重复 /v1"
    assert client.sanitize_base_url("localhost:1234") == "http://localhost:1234/v1", "需补全协议和 /v1"

    # 测试客户端重建
    new_config = dict(config)
    new_config["base_url"] = "http://localhost:11434/v1"
    new_config["api_key"] = ""
    client.update_config(new_config)
    assert client._base_url == "http://localhost:11434/v1", "update_config URL 未生效"

    print("[PASS] 测试 2: API 客户端与 URL 补全")


def test_prompt_builder():
    """测试 3: 提示词构建器"""
    from engine.prompt_builder import PromptBuilder

    # 无术语表
    prompt = PromptBuilder.build(style="无特定风格")
    assert "资深游戏本地化专家" in prompt, "基础角色缺失"
    assert "翻译铁律" in prompt, "铁律缺失"

    # 含术语表
    prompt = PromptBuilder.build(glossary={"HP": "生命值", "Elixir": "灵药"})
    assert "生命值" in prompt, "术语未注入"
    assert "灵药" in prompt, "术语未注入"

    # 含自定义提示词
    prompt = PromptBuilder.build(custom_prompt="把语气改得更傲娇一点")
    assert "傲娇" in prompt, "自定义提示词未注入"
    assert "用户特别要求" in prompt, "优先级标记缺失"

    # 风格预设
    prompt = PromptBuilder.build(style="二次元轻小说风")
    assert "轻小说" in prompt or "活泼" in prompt, "风格指令缺失"

    print("[PASS] 测试 3: 提示词构建器")


def test_text_guard():
    """测试 4: 文本安全检测"""
    from utils.text_guard import TextGuard

    # 乱码检测
    assert TextGuard.has_repeating_garbage("啊啊啊啊啊啊啊啊"), "应检测到重复乱码"
    assert not TextGuard.has_repeating_garbage("正常翻译结果"), "不应误判正常文本"

    # 占位符提取
    placeholders = TextGuard.extract_placeholders("Hello {name}, your HP is %d")
    assert "{name}" in placeholders or "{name}" in str(placeholders), "缺失 {name}"
    assert "%d" in placeholders, "缺失 %d"

    # 占位符验证
    missing = TextGuard.validate_placeholders("Hello {name}", "你好 {name}")
    assert len(missing) == 0, f"不应有缺失: {missing}"

    print("[PASS] 测试 4: 文本安全检测")


def test_extractor_via_detector():
    """测试 5: 引擎检测器"""
    from engine.extractor.detector import EngineDetector

    # 检测一个不存在目录的特征（应返回 unknown）
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        fake_exe = os.path.join(tmp, "fake.exe")
        with open(fake_exe, "w") as f:
            f.write("dummy")
        result = EngineDetector.detect(fake_exe)
        assert result == "unknown", f"不存在特征时应为 unknown, 实际: {result}"

    assert EngineDetector.get_friendly_name("rpgmaker_mv") == "RPG Maker MV"
    assert EngineDetector.get_friendly_name("unknown") == "未知引擎"

    print("[PASS] 测试 5: 引擎检测器")


def test_error_diagnosis():
    """测试 6: 错误诊断"""
    from utils.error_logger import diagnose_error, setup_error_logger

    logger = setup_error_logger()
    assert logger is not None, "日志初始化失败"

    title, advice = diagnose_error("PermissionError", "拒绝访问")
    assert title == "权限不足", f"权限错误应返回'权限不足', 实际: {title}"
    assert "管理员" in advice, "应提示管理员运行"

    title, advice = diagnose_error("ConnectionError", "")
    assert "网络" in title, "应检测到网络错误"

    title, advice = diagnose_error("UnknownThing", "")
    assert title == "未知错误", f"未知错误应返回兜底, 实际: {title}"

    print("[PASS] 测试 6: 错误诊断")


def test_security():
    """测试 7: 安全工具"""
    from utils.security import is_local_endpoint, get_privacy_badge, mask_api_key

    assert is_local_endpoint("http://localhost:1234/v1"), "localhost 应判定为本地"
    assert is_local_endpoint("http://127.0.0.1:11434/v1"), "127.0.0.1 应判定为本地"
    assert not is_local_endpoint("https://api.deepseek.com"), "DeepSeek 应为云端"

    badge, _, _ = get_privacy_badge("http://localhost:1234/v1")
    assert "本地" in badge, f"本地模式徽章错误: {badge}"

    masked = mask_api_key("sk-a1b2c3d4e5f6g7h8i9j0")
    assert len(masked) <= 20, f"掩码应缩短, 实际: {masked}"
    assert "sk-a" in masked, "掩码应保留前缀"

    print("[PASS] 测试 7: 安全工具")


def test_backup_manager():
    """测试 8: 备份管理器"""
    import tempfile
    from engine.backup_manager import BackupManager
    import shutil

    tmp = tempfile.mkdtemp()
    try:
        # 创建测试文件
        test_file = os.path.join(tmp, "test.json")
        with open(test_file, "w") as f:
            f.write('{"key": "value"}')

        mgr = BackupManager(tmp)
        assert mgr.backup_file("test.json"), "备份失败"
        assert mgr.is_backed_up(), "应检测到备份"
        assert mgr.restore_all() == 1, "应还原 1 个文件"

        # 清理注入产物
        cleaned = mgr.clean_injected_artifacts()
        assert isinstance(cleaned, dict), "清理结果应为 dict"

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("[PASS] 测试 8: 备份管理器")


def test_progress_tracker():
    """测试 9: 断点续传"""
    import tempfile
    import shutil
    from engine.progress_tracker import ProgressTracker

    tmp = tempfile.mkdtemp()
    try:
        # 需要把 ProgressTracker 的路径指向 tmp
        tracker = ProgressTracker.__new__(ProgressTracker)
        tracker._game_root = os.path.abspath(tmp)
        tracker._engine_type = "test"
        tracker._total = 100
        tracker._completed = set()
        tracker._progress_path = os.path.join(tmp, "translation_progress.json")

        assert tracker.pending_count == 100
        tracker.mark_completed(0)
        tracker.mark_completed(1)
        assert tracker.completed_count == 2
        assert tracker.get_pending_indices()[:3] == [2, 3, 4]

        tracker.start_timer()
        import time
        time.sleep(0.1)
        tracker.mark_completed(2)
        est = tracker.estimate_remaining()
        assert "秒" in est or "分钟" in est or "计算中" in est, f"预估异常: {est}"

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("[PASS] 测试 9: 断点续传")


if __name__ == "__main__":
    print("=" * 60)
    print("  游戏文本翻译工具 v4.0 — 端到端功能测试")
    print("=" * 60)

    tests = [
        test_config,
        test_api_client,
        test_prompt_builder,
        test_text_guard,
        test_extractor_via_detector,
        test_error_diagnosis,
        test_security,
        test_backup_manager,
        test_progress_tracker,
    ]

    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
        except Exception as e:
            print(f"[CRASH] {test.__name__}: {type(e).__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"  结果: {passed}/{len(tests)} 项测试通过")
    print(f"{'=' * 60}")