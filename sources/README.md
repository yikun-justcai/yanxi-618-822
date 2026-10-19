# 教材源文件（不随仓库分发）

出于版权考虑，本目录只保留说明，不提交四本教材的完整 OCR / MinerU 文本、扫描 PDF
或重点笔记原文件。仓库里的 `index.html` 是可直接运行的成品，不需要这些文件。

## 重建时需要的文件

`source_inventory.json` 中的 `ocrPath` 指向以下位置（相对站点根目录）：

```
sources/mineru/cai-wang-3.md
sources/mineru/chen-2.md
sources/mineru/ning-3.md
sources/mineru/xie-intro-5.md
sources/mineru/provenance.json
```

这些文件应由你自己合法持有的教材扫描件生成。项目此前使用的流程是：

1. 将 PDF 按 200 页以内分卷，提交 MinerU 精准解析（`vlm`、OCR、表格/公式开启）；
2. 用 `tools/mineru_import.py` 合并分卷、保留页序；
3. 用 `tools/mineru_to_ocr.py` 生成逐页文本，写入 `sources/mineru/`；
4. 运行 `python build_site.py`，构建会逐条回查教材引文。

## 没有源文件时

- 直接打开 `index.html` 即可使用整个站点；
- `python tools/selftest.py` 可以对成品页面运行回归测试；
- `python build_site.py` 会因找不到源文本而中止，这是有意的保护：不静默跳过引文校验。

## 版权

教材文本、引文与书名版权归原作者和出版社所有。请只使用你合法持有的副本，不要将
生成的全文文本提交到本仓库或其它公开位置。
