#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽帧总览图（contact sheet）+ 时间码对照表。

动手切素材之前先逐张看完：平台 UI、黑边、烧录字幕、主体动作在哪一秒，
都要从总览图上读出来，而不是凭时间码猜。

依赖：Python 3.8+ 标准库 + ffmpeg / ffprobe
      ffmpeg 不在 PATH 时用 FFMPEG_BIN / FFPROBE_BIN 指定绝对路径。

用法：
  python frame_overview.py input.mp4
  python frame_overview.py input.mp4 -o overview.jpg --fps 0.5 --cols 4 --width 320

输出：
  overview.jpg    拼好的总览图（格子按时间从左到右、从上到下）
  overview.txt    每个格子对应的时间码
"""

import argparse
import glob
import math
import os
import subprocess
import sys
import tempfile

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE_BIN", "ffprobe")


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def probe_duration(path):
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path])
    if r.returncode != 0:
        sys.exit("ffprobe 失败：%s" % r.stderr.decode("utf-8", "replace").strip())
    try:
        return float(r.stdout.decode().strip())
    except ValueError:
        sys.exit("读不到时长，确认输入是视频文件：%s" % path)


def main():
    ap = argparse.ArgumentParser(description="抽帧总览图 + 时间码表")
    ap.add_argument("input", help="输入视频")
    ap.add_argument("-o", "--output", default="overview.jpg", help="输出总览图（默认 overview.jpg）")
    ap.add_argument("--fps", type=float, default=1.0, help="每秒抽几帧（默认 1；长片可用 0.5）")
    ap.add_argument("--cols", type=int, default=4, help="每行几个格子（默认 4）")
    ap.add_argument("--width", type=int, default=320, help="单格宽度像素（默认 320）")
    a = ap.parse_args()

    src = os.path.abspath(a.input)
    out = os.path.abspath(a.output)
    if not os.path.isfile(src):
        sys.exit("找不到输入文件：%s" % src)
    if a.fps <= 0 or a.cols <= 0 or a.width <= 0:
        sys.exit("--fps / --cols / --width 必须为正数")

    duration = probe_duration(src)
    expected = max(1, int(math.ceil(duration * a.fps)))
    print("时长 %.2fs，按 %g fps 预计抽 %d 帧" % (duration, a.fps, expected))

    with tempfile.TemporaryDirectory(prefix="frames_") as tmp:
        pattern = os.path.join(tmp, "f_%04d.jpg")
        r = run([FFMPEG, "-v", "error", "-i", src,
                 "-vf", "fps=%s,scale=%d:-2" % (a.fps, a.width),
                 "-frames:v", str(expected), "-q:v", "3", "-y", pattern])
        if r.returncode != 0:
            sys.exit("ffmpeg 抽帧失败：%s" % r.stderr.decode("utf-8", "replace").strip())

        frames = sorted(glob.glob(os.path.join(tmp, "f_*.jpg")))
        if not frames:
            sys.exit("一帧都没抽出来，检查 ffmpeg 是否能解码这个视频")

        cols = min(a.cols, len(frames))
        rows = int(math.ceil(len(frames) / float(cols)))
        r = run([FFMPEG, "-v", "error", "-f", "image2", "-framerate", "1",
                 "-i", pattern,
                 "-vf", "tile=%dx%d:padding=6:margin=6:color=0xD2C6B6" % (cols, rows),
                 "-frames:v", "1", "-update", "1", "-q:v", "2", "-y", out])
        if r.returncode != 0:
            sys.exit("ffmpeg 拼图失败：%s" % r.stderr.decode("utf-8", "replace").strip())

    txt = os.path.splitext(out)[0] + ".txt"
    with open(txt, "w", encoding="utf-8") as f:
        f.write("# %s  时长 %.2fs  抽帧间隔 %.3fs (%g fps)\n" %
                (os.path.basename(src), duration, 1.0 / a.fps, a.fps))
        f.write("# 格子按「从左到右、从上到下」编号，编号从 1 开始\n")
        for i in range(len(frames)):
            t = i / a.fps
            f.write("格 %3d  ->  %02d:%06.3f  (%.3fs)\n" %
                    (i + 1, int(t // 60), t % 60, t))
        f.write("\n共 %d 格，%d 行 x %d 列\n" % (len(frames), rows, cols))

    print("已写出 %s  (%d 格，%dx%d)" % (out, len(frames), cols, rows))
    print("时间码表：%s" % txt)
    print("提示：先看第 0–1.2 秒有没有平台 UI / 标题条，结尾有没有烧录字幕。")


if __name__ == "__main__":
    main()
