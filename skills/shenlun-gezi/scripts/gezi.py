#!/usr/bin/env python3
"""申论答题卡格子模拟排版与字数统计。

用法:
  python3 gezi.py -l 300 [-w 25] [-i 0] [-f answer.txt]   # 不给 -f 则读 stdin

规则（与国考/省考答题卡惯例一致，可按需修改）:
  1. 汉字、全角标点各占 1 格。
  2. 半角字母/数字/半角符号(. % - / 等)两个挤 1 格：如 "1." "20" "22" "%"。
     "2022年" = 20|22|年 = 3 格；"98.4%" = 98|.4|% = 3 格。
  3. 两个标点连用（结束标点+后引号/后括号，如 。” ”。 ）。 ！”）合占 1 格。
  4. 行首不能出现点号/后引号/后括号：落到行首时挤进上一行最后一格，不新占格。
  5. 前引号/前括号/书名号前半不能留在行末：落到行末最后一格时移到下一行行首。
  6. 换行（新段落）后，本行剩余格子作废，但仍计入已用格数。
  7. 段首缩进 -i 格（概括题常为 0 以省格，大作文 2）。
  8. 省略号…… 破折号—— 各占 2 格，且不拆到两行。
统计口径：已用格数 = 最后一个字所在格的序号，即"写到第几格"，必须 <= 题目字数。
"""
import argparse
import sys

CLOSE_PUNCT = set("，。、；：？！”’）》」』】〉,;:?!)]")
END_PUNCT = set("，。、；：？！,;:?!")
CLOSE_QUOTE = set("”’）》」』】〉)]")
OPEN_PUNCT = set("“‘（《「『【〈([")
PAIR2 = ("……", "——")


def is_half(ch):
    return ord(ch) < 128 and not ch.isspace()


def tokenize(text):
    """把一段文字切成"格子单元"列表，每个单元是要写进一个(或两个)格子的字符串。"""
    toks = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in " \t\u3000":
            i += 1
            continue
        if text.startswith(PAIR2, i):
            toks.append(text[i:i + 2])  # 占 2 格的整体
            i += 2
            continue
        if is_half(ch) and ch not in CLOSE_PUNCT and ch not in OPEN_PUNCT:
            j = i
            while j < n and is_half(text[j]) and text[j] not in CLOSE_PUNCT - set(".") and text[j] not in OPEN_PUNCT:
                j += 1
            run = text[i:j]
            for k in range(0, len(run), 2):
                toks.append(run[k:k + 2])
            i = j
            continue
        # 标点连用合一格：结束点号+后引号，或后引号+结束点号
        if i + 1 < n and ch in CLOSE_PUNCT and text[i + 1] in CLOSE_PUNCT and (
            (ch in END_PUNCT and text[i + 1] in CLOSE_QUOTE) or
            (ch in CLOSE_QUOTE and text[i + 1] in END_PUNCT) or
            (ch in CLOSE_QUOTE and text[i + 1] in CLOSE_QUOTE)):
            toks.append(text[i:i + 2])
            i += 2
            continue
        toks.append(ch)
        i += 1
    return toks


def layout(paragraphs, width, indent):
    lines = []  # 每行是 cell 列表
    notes = []
    for p in paragraphs:
        line = [""] * indent
        for t in tokenize(p):
            if t in PAIR2:
                if len(line) + 2 > width:
                    lines.append(line)
                    line = []
                line += [t[0], t[1]]
                continue
            first = t[0]
            if first in CLOSE_PUNCT and len(line) == 0 and lines:
                lines[-1][-1] += t  # 行首禁则：挤进上一行末格
                notes.append(f"第{len(lines)}行末格挤入「{t}」")
                continue
            if len(line) == width:
                lines.append(line)
                line = []
                if first in CLOSE_PUNCT:
                    lines[-1][-1] += t
                    notes.append(f"第{len(lines)}行末格挤入「{t}」")
                    continue
            if first in OPEN_PUNCT and len(line) == width - 1:
                line.append("")  # 行末禁则：前引号不留行末
                lines.append(line)
                line = []
                notes.append(f"第{len(lines)}行末格空出（前引号移到下行）")
            line.append(t)
        if any(line):  # 段末标点挤进上一行后，不留空行
            lines.append(line)
    return lines, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-l", "--limit", type=int, required=True, help="题目字数上限=格子总数")
    ap.add_argument("-w", "--width", type=int, default=25, help="每行格数，默认25")
    ap.add_argument("-i", "--indent", type=int, default=0, help="段首缩进格数，默认0")
    ap.add_argument("--about", action="store_true", help="题目写的是'XX字左右'：目标区间为字数的90%%~110%%")
    ap.add_argument("--cells", type=int, help="答题卡实际格子总数（左右模式下作为硬上限，可选）")
    ap.add_argument("-f", "--file")
    ap.add_argument("--no-grid", action="store_true", help="不输出格子预览")
    a = ap.parse_args()
    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    paras = [p.strip() for p in text.replace("\r", "").split("\n") if p.strip()]
    lines, notes = layout(paras, a.width, a.indent)

    used = (len(lines) - 1) * a.width + len(lines[-1])
    filled = sum(1 for ln in lines for c in ln if c)
    wasted = used - filled
    if a.about:
        lo, hi = round(a.limit * 0.9), round(a.limit * 1.1)
        hard = a.cells
        cap = hard or hi
        max_lines = -(-cap // a.width)
        print(f"每行{a.width}格 | 题目约{a.limit}字（左右模式，目标{lo}~{hi}格"
              + (f"，答题卡共{hard}格" if hard else "") + f"） | 缩进{a.indent}")
    else:
        max_lines = -(-a.limit // a.width)
        print(f"每行{a.width}格 | 题目上限{a.limit}格（{max_lines}行） | 缩进{a.indent}")
    print(f"已用格数：{used}（写到第{len(lines)}行第{len(lines[-1])}格）")
    print(f"实写格数：{filled}  行末空格/缩进浪费：{wasted}")
    if a.about:
        if hard and used > hard:
            print(f"结果：❌ 超出答题卡 {used - hard} 格，写不下，必须删减")
        elif used > hi:
            print(f"结果：⚠️ 超出目标上沿 {used - hi} 格（{used / a.limit:.0%}），建议压缩到{hi}格内")
        elif used < lo:
            print(f"结果：⚠️ 偏少，差 {lo - used} 格到目标下沿（{used / a.limit:.0%}），建议补充")
        else:
            print(f"结果：✅ 在目标区间内（{used / a.limit:.0%}）")
    elif used <= a.limit:
        print(f"结果：✅ 未超，剩余 {a.limit - used} 格（{used / a.limit:.0%}）")
    else:
        print(f"结果：❌ 超出 {used - a.limit} 格，需删减")
    tails = []
    for k, ln in enumerate(lines[:-1]):
        if len(ln) < a.width and len(ln) <= 8:
            tails.append(f"第{k + 1}行只写{len(ln)}格（浪费{a.width - len(ln)}），该段删{len(ln)}格可省一整行")
    for t in tails:
        print("省行：" + t)
    for nt in notes:
        print("排版：" + nt)
    if not a.no_grid:
        print()
        for k, ln in enumerate(lines, 1):
            cells = []
            for c in ln:
                c = c or "　"
                cells.append(c if len(c) == 1 and not is_half(c) else (c + " " if len(c) == 1 else c))
            mark = ("  ◀答题卡末行" if a.about and a.cells else "  ◀目标上沿" if a.about else "  ◀上限") if k == max_lines else ""
            print(f"{k:>2}|{'|'.join(cells)}|{mark}")


if __name__ == "__main__":
    main()
