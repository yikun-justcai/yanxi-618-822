# Quickstart and Verification

1. 在项目根运行 `specify integration status`，确认 codex 与 dsh 完整。
2. 运行 `python source_inventory.py`，检查五份 OCR Markdown 均登记且源文件未被修改。
3. 运行 `python build_cards.py`，确认课程引用和题卡 ID 校验通过，并保持原有题卡数量。
4. 断网后双击 `index.html`：分别进入 618 与 822 第一课，完成自检并打开关联题卡，查看答案、评分，再回课程；刷新检查状态。
5. 通过本地 HTTP 预览在 390px、1440px、1728px 检查导航、滚动、焦点、题卡评分与无横向溢出；静态检查不能替代此步。
6. 对每科至少抽三处出处，按“OCR 第 N 页”回查 Markdown 与原 PDF；不一致的课程退回待复核。

学生端完全离线。`mineru-textbook-to-md` 只供维护者准备资料，当前已有 OCR 时不需 Token；任何 PDF 上传须另行确认授权与目标文件。
