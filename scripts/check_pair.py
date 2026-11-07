#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首尾帧能否配对：把「同机位、同景别、同朝向、且真有位移」变成可测数字。

图生视频的三条铁律里，第 2 条最容易翻车：尾帧由首帧派生、提示词写「位置不变」，
结果整段运动量只有 1.55，等于一张会呼吸的静图。这个脚本在送进模型之前就把这件事挡下来。

指标：两张图统一缩到 160x90 灰度，逐像素算平均绝对差（0–255），
      以及变化超过 10 级的像素占比。

依赖：Python 3.8+ 标准库 + ffmpeg / ffprobe
      ffmpeg 不在 PATH 时用 FFMPEG_BIN / FFPROBE_BIN 指定绝对路径。

用法：
  python check_pair.py first.jpg last.jpg
  python check_pair.py first.png last.png --too-similar 2 --too-different 45
"""

import argparse
import os
import subprocess
import sys

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE_BIN", "ffprobe")
W, H = 160, 90
N = W * H


def probe(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height",
                        "-of", "csv=p=0:s=x", path],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        sys.exit("ffprobe 失败：%s" % r.stderr.decode("utf-8", "replace").strip())
    return r.stdout.decode().strip()


def gray(path):
    r = subprocess.run([FFMPEG, "-v", "error", "-i", os.path.abspath(path),
                        "-vf", "scale=%d:%d,format=gray" % (W, H),
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0 or len(r.stdout) != N:
        sys.exit("ffmpeg 解码失败（%s）：%s" %
                 (path, r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description="校验首尾帧是否可配对")
    ap.add_argument("first", help="首帧图片")
    ap.add_argument("last", help="尾帧图片")
    ap.add_argument("--too-similar", type=float, default=2.0,
                    help="平均差低于此值判为「没动」（默认 2.0）")
    ap.add_argument("--too-different", type=float, default=45.0,
                    help="平均差高于此值判为「跨机位/换主体」（默认 45.0）")
    a = ap.parse_args()

    for p in (a.first, a.last):
        if not os.path.isfile(p):
            sys.exit("找不到文件：%s" % p)

    s1, s2 = probe(a.first), probe(a.last)
    print("首帧 %s  %s" % (os.path.basename(a.first), s1))
    print("尾帧 %s  %s" % (os.path.basename(a.last), s2))
    if s1 != s2:
        sys.exit("\n[FAIL] 尺寸不一致。首尾帧必须同尺寸、同景别，先统一再生成。")

    b1, b2 = gray(a.first), gray(a.last)
    total = 0
    changed = 0
    for x, y in zip(b1, b2):
        d = abs(x - y)
        total += d
        if d > 10:
            changed += 1
    mean = total / float(N)
    ratio = 100.0 * changed / N

    print("\n平均绝对差 %.2f / 255，明显变化像素 %.1f%%" % (mean, ratio))

    if mean < a.too_similar:
        print("[FAIL] 首尾几乎没差别。模型会给出静帧——")
        print("       把那个要动的物体在尾帧里真的挪开，或换一段动作更明显的素材。")
        print("       参考基线：尾帧由首帧派生 + 提示词写「位置不变」= 全片运动量 1.55。")
        sys.exit(2)
    if mean > a.too_different:
        print("[WARN] 差异过大。检查是不是跨了机位 / 景别 / 人物朝向，")
        print("       或者换了个主体。跨机位模型不会给你蜕变，只会死守首帧；")
        print("       要大景别跳跃请剪硬切，别让模型变形。")
        sys.exit(3)

    print("[OK] 可以配对：同尺寸、有位移、差异没有大到像换镜头。")
    print("     接着仍要肉眼确认：机位没动、光照没变朝向、要动的物体在首帧里就已经存在。")


if __name__ == "__main__":
    main()
