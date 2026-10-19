# Lesson Data Contract

生成端读取 `lesson_content.py` 中的 `LESSONS`；每项必须满足 [data-model.md](../data-model.md) 的 Unit 字段，且 `reviewStatus == "verified"`、每个 `sourceRef` 的 OCR 页为正整数、每个 `cardId` 存在于题库。校验失败则 `build_cards.py` 报错并保持旧 HTML 不变。

生成端将课程 JSON 写入 `<script id="lesson-data" type="application/json">`，对 `<` 做安全转义，避免数据中出现 `</script>` 破坏文档。学生端不能在运行时读取 OCR 文件、发起网络请求或调用模型。

学生端导航契约：`学习路径` 显示两科单元目录；选择单元显示目标、解释、关联概念、自检、OCR 出处；`练这道题` 打开对应题卡；从题卡能返回刚才的单元。不存在关联题卡时显示明确空态。
