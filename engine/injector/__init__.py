# -*- coding: utf-8 -*-
"""
注入器子包 v4.0

注入层级:
  1. FileInjector — 常规文件注入 (RPG Maker JSON覆写 + Ren'Py .rpy生成)
  2. MemoryInjector — 强制内存注入 (当FileInjector连续10次失败时触发)
"""

from engine.injector.base_injector import BaseInjector, InjectionState, RetryCategory, InjectionRetryCounter
from engine.injector.file_injector import FileInjector
from engine.injector.memory_injector import MemoryInjector