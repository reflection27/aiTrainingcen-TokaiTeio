# -*- coding: utf-8 -*-
"""
点歌工具
支持 QQ音乐 和 网易云音乐

TODO:
  - QQ音乐：接入 QQ音乐 API（需要 Cookie / OAuth）
  - 网易云音乐：接入 NeteaseCloudMusicApi（开源 Node.js 服务）
    或直接使用 pyncm / pycloudmusic 等 Python 库
"""

from typing import Any, Dict, List

PLATFORM_QQ = "qq"
PLATFORM_NETEASE = "netease"
SUPPORTED_PLATFORMS = (PLATFORM_QQ, PLATFORM_NETEASE)


class MusicTool:
    """点歌工具（占位实现）"""

    # ------------------------------------------------------------------ #
    #  公开接口                                                             #
    # ------------------------------------------------------------------ #

    def search_song(self, keyword: str, platform: str = PLATFORM_NETEASE, limit: int = 5) -> str:
        """
        搜索歌曲

        Args:
            keyword:  搜索关键词，如 "周杰伦 晴天"
            platform: "qq" 或 "netease"，默认网易云
            limit:    返回结果数量，默认 5

        Returns:
            JSON 格式的搜索结果字符串
        """
        self._check_platform(platform)
        if platform == PLATFORM_QQ:
            return self._qq_search(keyword, limit)
        return self._netease_search(keyword, limit)

    def play_song(self, song_id: str, platform: str = PLATFORM_NETEASE) -> str:
        """
        获取歌曲播放链接

        Args:
            song_id:  平台侧歌曲 ID
            platform: "qq" 或 "netease"

        Returns:
            播放 URL 字符串
        """
        self._check_platform(platform)
        if platform == PLATFORM_QQ:
            return self._qq_play(song_id)
        return self._netease_play(song_id)

    def get_playlist(self, playlist_id: str, platform: str = PLATFORM_NETEASE) -> str:
        """
        获取歌单曲目列表

        Args:
            playlist_id: 平台侧歌单 ID
            platform:    "qq" 或 "netease"

        Returns:
            JSON 格式的歌单信息字符串
        """
        self._check_platform(platform)
        if platform == PLATFORM_QQ:
            return self._qq_playlist(playlist_id)
        return self._netease_playlist(playlist_id)

    # ------------------------------------------------------------------ #
    #  QQ音乐（待实现）                                                     #
    # ------------------------------------------------------------------ #

    def _qq_search(self, keyword: str, limit: int) -> str:
        # TODO: 调用 QQ音乐搜索接口
        # 参考：https://github.com/jsososo/QQMusicApi
        return f"[QQ音乐] 搜索 '{keyword}' —— 接口尚未实现"

    def _qq_play(self, song_id: str) -> str:
        # TODO: 获取 QQ音乐播放链接
        return f"[QQ音乐] 歌曲 {song_id} 播放链接 —— 接口尚未实现"

    def _qq_playlist(self, playlist_id: str) -> str:
        # TODO: 获取 QQ音乐歌单
        return f"[QQ音乐] 歌单 {playlist_id} —— 接口尚未实现"

    # ------------------------------------------------------------------ #
    #  网易云音乐（待实现）                                                  #
    # ------------------------------------------------------------------ #

    def _netease_search(self, keyword: str, limit: int) -> str:
        # TODO: 调用 NeteaseCloudMusicApi 或 pyncm
        # 参考：https://github.com/Binaryify/NeteaseCloudMusicApi
        return f"[网易云] 搜索 '{keyword}' —— 接口尚未实现"

    def _netease_play(self, song_id: str) -> str:
        # TODO: 获取网易云播放链接
        return f"[网易云] 歌曲 {song_id} 播放链接 —— 接口尚未实现"

    def _netease_playlist(self, playlist_id: str) -> str:
        # TODO: 获取网易云歌单
        return f"[网易云] 歌单 {playlist_id} —— 接口尚未实现"

    # ------------------------------------------------------------------ #
    #  内部工具                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _check_platform(platform: str):
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}，可选: {SUPPORTED_PLATFORMS}")
