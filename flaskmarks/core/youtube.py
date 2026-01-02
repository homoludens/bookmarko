"""
YouTube video information extraction utilities.
"""
from __future__ import annotations

import re
from typing import Any, TypedDict

import requests
import yt_dlp


class YouTubeInfo(TypedDict):
    """Type definition for YouTube video information."""
    duration: int | None
    categories: list[str]
    uploader: str | None
    description: str
    tags: list[str]
    subtitles: str
    channel_name: str | None
    youtube_type: str
    title: str


def download_subtitles(subtitles_url: str | None) -> str:
    """
    Download subtitles from URL found with yt_dlp.

    Args:
        subtitles_url: URL to the subtitles file

    Returns:
        Cleaned subtitle text with timestamps removed
    """
    if not subtitles_url:
        return ''

    response = requests.get(subtitles_url, stream=True)

    # Remove timestamps and formatting
    pattern = (
        r'<c>|<\/c>|<\d{2}\W\d{2}\W\d{2}\W\d{3}>|'
        r'align:start position:0%|'
        r'\d{2}\W\d{2}\W\d{2}\W\d{3}\s\W{3}\s\d{2}\W\d{2}\W\d{2}\W\d{3}'
    )
    subtitles = re.sub(pattern, '', response.text)

    return subtitles


def get_youtube_info(youtube_url: str) -> YouTubeInfo:
    """
    Get information about a YouTube video.

    Args:
        youtube_url: URL to the YouTube video

    Returns:
        Dictionary containing video metadata and subtitles
    """
    ydl_opts: dict[str, Any] = {
        'write_auto_sub': True,
        'sub_lang': 'en',
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'noplaylist': True,
        'playlist_items': '1',
        'quiet': True,
    }

    res_subtitles = ''

    ydl = yt_dlp.YoutubeDL(ydl_opts)
    res = ydl.extract_info(youtube_url, download=False)

    url_type = 'video'
    if 'vcodec' not in res:
        url_type = 'channel'
    else:
        try:
            res_subtitles = download_subtitles(
                res['requested_subtitles']['en']['url']
            )
        except (KeyError, TypeError):
            pass

    return {
        'duration': res.get('duration'),
        'categories': res.get('categories', []),
        'uploader': res.get('uploader'),
        'description': res.get('description', ''),
        'tags': res.get('tags', []),
        'subtitles': res_subtitles,
        'channel_name': res.get('uploader'),
        'youtube_type': url_type,
        'title': res.get('title', youtube_url),
    }


def check_url_video(url: str) -> bool:
    """
    Check if URL is supported by yt-dlp.

    Args:
        url: URL to check

    Returns:
        True if URL is a valid video, False otherwise
    """
    ydl = yt_dlp.YoutubeDL({
        'quiet': True,
        'noplaylist': True,
        'playlist_items': '1',
    })

    try:
        info = ydl.extract_info(url, download=False)
        if info.get('channel_id') == '':
            return False
        return True
    except Exception:
        return False
