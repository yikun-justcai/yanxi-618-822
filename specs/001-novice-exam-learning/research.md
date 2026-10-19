# Phase 0 Research

## Decision 1: 保留离线单页

- **Decision**: 延续 `index.html`、原生 JS 和 `build_cards.py`。
- **Rationale**: 现有题卡、离线打开和本地进度已工作；课程可作为第二份嵌入数据加入。
- **Alternatives considered**: React／服务端课程库会引入打包、部署和运行依赖，首版无此需要。

## Decision 2: 复用已有 OCR，先人工校页

- **Decision**: 五份 OCR Markdown 位于 `D:\考研备考\OCR全文`；只在项目中登记来源和改写后的短课，不复制整书。
- **Evidence**: 目录中有五份约 1–1.8 MB 的 Markdown；文件以 `## 第 N 页` 记录 OCR 页。部分原 PDF 的文本层为空。
- **Alternatives considered**: 重新上传 MinerU。已有文本可先满足定位与审校，重复上传增加版权和隐私边界。

## Decision 3: MinerU Skill 用于预检和未来修复

- **Decision**: `ber-ners/mineru-textbook-to-md` 安装在项目 `.agents/skills` 与 `.dsh/skills`。当前只运行本地 `--dry-run`。
- **Evidence**: 对《公共政策导论》第五版现有 OCR 运行试拆后，报告 162 个候选“章节”及 162 个复核标记，明显把页眉重复标题误作章节；没有写入文件。
- **Consequences**: 不采用自动拆分结果；先按页标记和人工目录校验建立小批课程。若以后上传 PDF，先确定具体文件、输出位置及用户上传授权。

## Decision 4: 共用 Spec Kit，不预装 DSH 程序

- **Decision**: 以 Codex 为默认集成，另安装 `dsh` 集成。两者读写 `.specify` 同一规格。
- **Evidence**: `specify integration status` 返回 codex、dsh 且无缺失托管文件。`specify check` 表明本机没有 `dsh` 可执行程序。
- **Consequences**: 项目已准备好 DSH 参与开发；实际启动 DSH 需另行安装运行程序。安装第三方软件时遵守 `C:\application\<项目名>` 偏好。

## Decision 5: 内容质量比自动扩量优先

- **Decision**: 首批只发布经 OCR 页段抽核的 618 和 822 入门单元，并保留逐章缺口表。
- **Rationale**: 批量生成整书课程会把 OCR 错字和不同版本术语不加区分地带入学生端。
- **Alternatives considered**: 自动生成全部题卡或全文检索页。它们不能替代新手解释与作答训练。
