# ai-video-storyboard-frames

**AI 视频实操手册：从实拍素材到图生视频成片。**

不是提示词合集，也不是模型测评。这是一份在真实片子上反复翻车后写下来的判断手册：
什么时候该抽帧、什么时候该直接放弃这段、首尾帧到底配不配得上、模型根本做不出来的动作该怎么写、
成片到底动没动——**全部给数值，不靠眼睛**。

> A field manual for image-to-video production. It is about deciding what a model can and cannot do
> before you spend a generation: frame extraction, first/last-frame pairing, prompt structure for
> first-frame / last-frame mode, ffmpeg-only repair, and quantitative motion checks.
> Every rule here came from a failed render, with the measured numbers kept.

## 它解决什么问题

图生视频最常见的失败不是「画质不好」，是**花了钱生成了一段不会动的静图**，
或者让模型去做它结构上就做不到的事：凭空长出一个物体、跨机位蜕变、手从画外伸进来。

这份手册把这些限制变成可执行的检查项：

1. 抽帧总览先看清素材，再决定切哪一帧
2. 首尾帧必须同机位、同景别、同朝向，且**要动的物体真的换了位置**
3. 生成完用逐帧差均值验「有没有真的动」

## 三条铁律（SKILL.md 第三节）

| | 规则 | 翻车现场 |
|---|---|---|
| 1 | **不能凭空新增物体** | 让「手从画外伸进来」而首帧里没有手 → 模型干脆不做 |
| 2 | **要它动，首尾帧里那个东西就必须真的换了位置** | 尾帧由首帧派生 + 提示词写「位置不变」→ 全片运动量 **1.55**，等于静帧 |
| 3 | **首尾帧必须同机位、同景别、同朝向** | 跨机位不会给你蜕变，只会死守首帧；想要景别跳跃请剪硬切 |

配套的可测指标：亮度曲线判断「点亮」是否发生、逐帧差均值判断有没有运动、
`crop` 固定值先把自产图的角标裁掉再转 16:9（**写提示词时就要为这个裁切留余量**）。

## 十六节里有什么

| 节 | 主题 |
|---|---|
| 0 | 环境、素材来源与合规 |
| 1–3 | 抽帧总览、带平台 UI 的素材、三条铁律与量化验证 |
| 4–7 | 图生图补帧、造上摇落点帧、图生视频提示词 ≠ 图生图、交付目录约定 |
| 8–12 | 纯 ffmpeg 修瑕疵、只移动画面里某一个物体、把动作补完整、动手前先读懂画面、瑕疵是生成的还是参考图里就有的 |
| 13–16 | 传统题材考据、新素材复核、拿别人的短片当节奏模板（题材置换法）、工艺流程片与人物动作片的两种相反逻辑 |
| 附录 | 平台截图只作形制参考、剪映 SRT、成片对轴切点检测、细杆件光位、锁机位、点亮／描线／平涂等难动作逐项拆法 |

第十五节明确写死了**不能借的东西**：原片任何一帧、原文案与字幕、UP 主 ID、弹幕、原工具水印。
借的只是节奏和结构。

## 三个可直接跑的脚本

只用 **Python 3.8+ 标准库 + ffmpeg**，不需要 numpy、opencv 或任何 pip 包。
ffmpeg 不在 PATH 时用 `FFMPEG_BIN` / `FFPROBE_BIN` 指定绝对路径。

```bash
# ① 抽帧总览 + 时间码表：动手前先逐张看完
python scripts/frame_overview.py input.mp4 -o overview.jpg --fps 1 --cols 4
#    -> overview.jpg（拼好的总览图）+ overview.txt（每格对应几秒）

# ② 送进模型前，验首尾帧配不配得上
python scripts/check_pair.py first.jpg last.jpg
#    尺寸不一致 -> FAIL；平均差 < 2 -> 模型会给静帧；> 45 -> 怀疑跨机位/换主体

# ③ 生成完，验成片到底动没动
python scripts/motion_amount.py out.mp4 --report motion.txt
#    均值 < 2 基本等于静帧，2–8 只有呼吸/光变，>= 8 才算有明显运动
```

三个脚本的阈值都可用命令行参数覆盖，退出码也做了区分（`2` = 静帧 / `3` = 差异过大），
可以直接接进自己的批处理。

## 安装为一个 Agent Skill

这是一个 `SKILL.md` 格式的技能，给会读本地文件的编码 Agent 用。

```bash
git clone https://github.com/WXM-ABC/ai-video-storyboard-frames.git
mv ai-video-storyboard-frames ~/.workbuddy/skills/ai-video-storyboard-frames
# 或项目级
# mv ai-video-storyboard-frames .claude/skills/ai-video-storyboard-frames
```

之后对 Agent 说「把这段视频做成 AI 视频素材」「帮我看看首尾帧能不能配对」
「这段怎么没动」就会触发。不想装 git 的，也可以从
[Releases](https://github.com/WXM-ABC/ai-video-storyboard-frames/releases/latest) 下源码包。

## 环境

- ffmpeg + ffprobe 在 PATH（Windows 上 Git-Bash 里读文件要用 `C:/...` 正斜杠绝对路径）
- Python 3.8+，标准库即可
- 像素级 inpaint / 光流若自备 numpy + opencv 会更省事，但**不是必需**

## 合规与来源

- 本仓库**不含任何视频、图片、音频素材**，只有文字手册与三个脚本。
- 手册讨论的实拍素材与参考片默认是你自己拍摄或有权使用的。处理带平台 UI 的截图时，
  正确做法是避开该时段或重新构图、仅作形制参考；**不要以去除他人署名、规避版权标识为目的做修补**。
- 文中出现的平台与模型名称仅作产品指代，不代表任何背书或隶属关系。
- 所有数值来自具体机器的实测记录，换设备、换模型版本请重新量一次再用。

## 许可

代码与文档以 **MIT** 发布，见 [LICENSE](LICENSE)。第三方组件声明见 [NOTICE.md](NOTICE.md)。
