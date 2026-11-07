#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成片到底动没动：逐帧差均值，别靠眼睛。

生成完别看缩略图就交付。把整段视频缩到 160x90 灰度，逐帧算平均绝对差，
得到一条运动量曲线和一个总均值。经验阈值（见 SKILL.md 第三节）：

  < 2    基本等于静帧，白花钱
  2–8    只有轻微呼吸/光变，动作没做出来
  >= 8   有明显运动，可以进入下一步审片

依赖：Python 3.8+ 标准库 + ffmpeg
      ffmpeg 不在 PATH 时用 FFMPEG_BIN 指定绝对路径。

用法：
  python motion_amount.py out.mp4
  python motion_amount.py out.mp4 --report motion.txt
"""

import argparse
import os
import subprocess
import sys

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
W, H = 160, 90
N = W * H


def read_exact(stream, n):
    buf = b""
    while len(buf) < n:
        chunk = stream.read(n - len(buf))
        if not chunk:
            break
        buf += chunk
    return buf


def main():
    ap = argparse.ArgumentParser(description="量化成片运动量")
    ap.add_argument("input", help="输入视频")
    ap.add_argument("--report", help="可选：把逐帧差值写到文本文件")
    a = ap.parse_args()

    src = os.path.abspath(a.input)
    if not os.path.isfile(src):
        sys.exit("找不到文件：%s" % src)

    cmd = [FFMPEG, "-v", "error", "-i", src,
           "-vf", "scale=%d:%d,format=gray" % (W, H),
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    diffs = []
    prev = None
    while True:
        cur = read_exact(p.stdout, N)
        if len(cur) != N:
            break
        if prev is not None:
            total = sum(abs(x - y) for x, y in zip(prev, cur))
            diffs.append(total / float(N))
        prev = cur
    err = p.stderr.read().decode("utf-8", "replace").strip()
    p.wait()

    if not diffs:
        sys.exit("一帧都没读出来，检查 ffmpeg 是否能解码：%s" % (err or "未知错误"))

    mean = sum(diffs) / len(diffs)
    peak = max(diffs)
    still = sum(1 for d in diffs if d < 0.5)
    print("帧数 %d，逐帧差 %d 条" % (len(diffs) + 1, len(diffs)))
    print("均值 %.2f / 255，峰值 %.2f，几乎静止的帧 %.1f%%" %
          (mean, peak, 100.0 * still / len(diffs)))

    if mean < 2:
        print("\n[FAIL] 基本等于静帧。首尾帧没真的错位，或提示词没能把动作逼出来。")
        verdict = "FAIL 静帧"
    elif mean < 8:
        print("\n[WARN] 只有轻微变化（呼吸、光变、压缩噪声）。想要的是位移，不是亮度。")
        verdict = "WARN 运动偏弱"
    else:
        print("\n[OK] 有明显运动。下一步做切点检测与带时间码的抽帧总览。")
        verdict = "OK"

    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            f.write("# frame_diff for %s\n# mean=%.4f peak=%.4f verdict=%s\n" %
                    (os.path.basename(src), mean, peak, verdict))
            for i, d in enumerate(diffs):
                f.write("%d %.4f\n" % (i, d))
        print("逐帧曲线：%s" % a.report)

    sys.exit(2 if mean < 2 else 0)


if __name__ == "__main__":
    main()
