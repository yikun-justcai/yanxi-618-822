# Implementation Plan: 618／822 从入门到真题的离线学习站

**Branch**: `001-novice-exam-learning`（目录标识，无 Git 仓库） | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-novice-exam-learning/spec.md`

## Summary

保留现有单页离线题卡站和 `yanxi-study-v1` 数据，在同一应用壳内增加“学习路径”。课程内容单独维护并由现有 Python 生成器嵌入，避免运行时请求。每个已发布单元以教材 OCR 页码与人工抽核记录为前提，链接既有题卡。Spec Kit 为 Codex 与 DSH 提供同一份需求和任务。

## Technical Context

**Language/Version**: HTML、CSS、原生 JavaScript；Python 3.10+ 内容生成脚本  
**Primary Dependencies**: 学生端无依赖；生成端沿用 `python-docx`，内容盘点使用标准库；教材转换 Skill 自带 `pypdf`、`requests`  
**Storage**: 嵌入式 JSON 题库和课程；现有 `localStorage` 学习记录  
**Testing**: Python 数据校验；本地 HTTP 浏览器交互、键盘和 390px／1440px 截图及 DOM 测量  
**Target Platform**: Windows 本地浏览器，可通过 `file://` 双击打开；验证可用本地 HTTP 预览  
**Project Type**: 离线单页网站  
**Performance Goals**: 275 张题卡与首批课程在普通电脑上即时切换；不额外加载完整教材 OCR  
**Constraints**: 不上云、不引入账号、不得在前端嵌入教材全文或密钥，保留现有题库生成器和用户进度  
**Scale/Scope**: 618、822 两科；先实现各科入门链，再逐章扩至教材和真题覆盖

## Constitution Check

- 618／822 唯一考试范围：通过。
- OCR 证据可追溯：课程数据模型要求 `sourceId`、`ocrPage`、`reviewStatus`；未经核对不发布。
- 新手理解到输出：单元结构包括解释、关系、自检和关联题卡；通过。
- 离线及原进度：无运行时网络，沿用原存储键并另存单元状态；通过。
- Better Design 原则及实际评审：完成视觉和流程检查后方可宣称 UI 完成。

## Project Structure

### Documentation (this feature)

```text
specs/001-novice-exam-learning/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/lesson-data.md
└── tasks.md
```

### Source Code (project root)

```text
index.html                   # 学生端离线 UI 与题库、课程嵌入数据
build_cards.py              # 现有 DOCX／真题生成器，扩展课程嵌入与校验
lesson_content.py           # 人工审校的短篇课程与来源定位
source_inventory.py         # 本地 OCR 文件盘点，输出清单而非教材全文
source_inventory.json       # 本机教材来源、页数和待核对状态
使用说明.md                  # 使用与内容维护说明
.specify/                   # 共用工作流
.agents/skills/             # Codex Spec Kit 与 MinerU Skill
.dsh/skills/                # DeepSeek Harness Spec Kit 与 MinerU Skill
```

**Structure Decision**: 保留单文件学生端以满足离线双击使用。生成与审校数据分开，不能在 `index.html` 中手工修改嵌入题库或课程 JSON。

## Phase 0: Research Decisions

见 [research.md](research.md)。核心决定：复用已有五份 OCR Markdown；MinerU Skill 仅用于后续缺失或低质量页的项目级转换，上传前需明确文件及授权；暂不安装 DSH 运行程序。

## Phase 1: Design and Contracts

见 [data-model.md](data-model.md)、[contracts/lesson-data.md](contracts/lesson-data.md) 和 [quickstart.md](quickstart.md)。课程单元状态与题卡评分状态分离；现有题卡 ID 不重排。

## Complexity Tracking

无宪章例外。暂不迁移 React 或新增服务端，因为会破坏简单的本地离线使用方式，且现有模式足以完成首版学习路径。
