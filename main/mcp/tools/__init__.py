# -*- coding: utf-8 -*-
"""
MCP工具集合
在此处导入并注册所有工具模块
"""

from main.mcp.tools.music import MusicTool


def register_all(server):
    """将所有工具注册到 MCPServer"""
    music = MusicTool()
    server.register(
        "search_song",
        music.search_song,
        description="搜索歌曲（支持QQ音乐/网易云音乐）",
        params=["keyword", "platform", "limit"],
    )
    server.register(
        "play_song",
        music.play_song,
        description="播放指定歌曲",
        params=["song_id", "platform"],
    )
    server.register(
        "get_playlist",
        music.get_playlist,
        description="获取歌单",
        params=["playlist_id", "platform"],
    )
