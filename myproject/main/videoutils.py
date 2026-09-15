import math

def detect_duration_seconds(path):
    try:
        import imageio_ffmpeg
        reader = imageio_ffmpeg.read_frames(path)
        meta = next(reader)
        reader.close()
        duration = float(meta.get('duration') or 0)
        return duration if duration > 0 else 0
    except Exception:
        return 0

def detect_duration_minutes(path):
    seconds = detect_duration_seconds(path)
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / 60))
