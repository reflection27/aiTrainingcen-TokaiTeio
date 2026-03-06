# -*- coding: utf-8 -*-
# 临时model.py文件，用于解决模块导入问题
# 根据错误信息，funasr尝试从model模块加载远程代码
# 我们创建一个空的model模块，避免导入错误
import sys
import os

# 定义一个空的SenseVoiceSmall类，避免导入错误
class SenseVoiceSmall:
    pass

# 导出所有公共类和函数
__all__ = ['SenseVoiceSmall']
