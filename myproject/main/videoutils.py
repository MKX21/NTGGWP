"""
影片工具：上傳影片後自動偵測時長（老師不需手動輸入分鐘數）。
使用 imageio-ffmpeg 內建的可攜式 ffmpeg，不需系統另裝 ffmpeg。
"""
import math


def detect_duration_seconds(path):
    """回傳影片秒數（float）；無法解析時回傳 0。"""
    try:
        import imageio_ffmpeg
        reader = imageio_ffmpeg.read_frames(path)
        meta = next(reader)  # 第一個 yield 是 metadata（含 duration）
        reader.close()
        duration = float(meta.get('duration') or 0)
        return duration if duration > 0 else 0
    except Exception:
        return 0


def detect_duration_minutes(path):
    """回傳影片分鐘數（無條件進位，至少 1 分）；無法解析回傳 0。"""
    seconds = detect_duration_seconds(path)
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / 60))
