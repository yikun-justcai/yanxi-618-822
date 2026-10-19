# Data Model

## Source

`id`（稳定键）、`title`、`edition`、`subject`（618／822）、`ocrPath`、`pdfPath`（可空）、`pageMarker`（固定为 OCR 页）、`pageCount`、`reviewStatus`。原始路径仅用于维护工具，不进入学生端。审核状态为 `unreviewed`、`sampled`、`verified`。

## Unit

`id`、`subject`、`order`、`title`、`goal`、`explanation`、`connections`、`checkQuestion`、`sourceRefs[]`、`cardIds[]`、`reviewStatus`。`sourceRefs` 包括 `sourceId`、`ocrPage`、`locatorNote`。学生端仅嵌入 `verified` 单元。`cardIds` 可以为空，但 UI 必须说明暂无配套题。

## Card

沿用现有 ID 和字段：`course`、`chapter`、`question`、`answer`、`source`，真题另含 `kind`、`year`、`questionType`、`basis`。新单元只能引用已存在的卡片 ID，不重命名旧 ID。

## LearnerProgress

旧数据：`yanxi-study-v1` 下的 `progress`、`custom` 原样保留。新数据：独立键记录已学单元 ID 与最后打开的单元；读取失败时回退为空状态并提示无法保存。单元“已学过”只说明用户完成自检操作，不推断掌握程度。

## State Transitions

课程：未打开 → 阅读中 → 已自检；可随时重读。题卡：未揭示 → 已揭示 → 自评分 → 根据现有间隔安排复习。课程与题卡状态不互相覆盖。
