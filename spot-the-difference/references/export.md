# 发布与坐标约定

先选用项目原有的校验和导出入口。若只有已经对齐的图对和计划改动范围，可用本技能的 `scripts/export_levels.py`。它需要 Python 3.10+、Pillow 和 NumPy，读取文件并生成本地导出目录。它不需要模型账号，也不会发起网络请求。

## 输入

在 JSON 中按关卡顺序列出图片和区域。图片路径相对于清单文件。`modified` 应是合成后的无损图，尺寸及显示方向与原图一致。若实际发布的是同一成品的 JPEG，可用可选的 `delivery` 指向它。脚本校验 JPEG 与无损图的像素偏差，答案仍从无损图提取。数值 `score` 和 `difficulty` 可沿用该项目对本次成品的评分。`count` 可省略，提供时须与改动区域数吻合。

```json
{
  "levels": [
    {
      "id": "lv032",
      "original": "source/lv032_a.jpg",
      "modified": "composite/lv032_b.png",
      "delivery": "release/lv032_b.jpg",
      "count": 2,
      "score": 44,
      "difficulty": "标准",
      "regions": [
        {"box": [430, 53, 492, 124], "kind": "发夹替换", "source": "cloudflare", "model": "FLUX.2 Klein 4B"},
        {"box": [604, 180, 636, 218], "kind": "挂饰换色", "source": "local"}
      ]
    }
  ]
}
```

```text
python scripts/export_levels.py job.json export
```

指定 `--check-progression` 时，检查清单顺序中的已提供分数和差异点数都不下降。此选项不计算难度分数。脚本先写入同目录的临时位置，通过后发布为目标目录。已存在的目标需另选发布位置或明确授权替换。批量写回现有游戏文件夹时，先比对其原图及现有差异图的版本，再安全发布。

## 坐标和文件

- 以图像左上角为 `(0, 0)`。输入 `box` 及导出的 `editBox` 格式是 `[left, top, right, bottom]`，右和下不含边界。导出的 `bbox` 是实际差异的外接框，格式为 `[x, y, width, height]`。
- `point` 是落在差异内的像素坐标。`pointNormalized` 对应这个像素的中心，`bboxNormalized` 由实际外接框按宽高归一化。保持前端点击映射到原图坐标，别直接使用页面像素。
- 输出使用关卡 ID 加 `_a`/`_b` 后缀，保留正常图片格式。`masks/` 是灰度 PNG，0 为未变区域，1 起对应差异 ID。
- `关卡与差异.json` 每关记录对应图片、遮罩和答案。`差异信息表.csv` 每行一点，记录差异框、命中点、来源及像素变化。`关卡总表.csv` 每行一关，CSV 使用 UTF-8 BOM。发布后核对关卡数、差异总数、文件名匹配和旧版是否可恢复。
