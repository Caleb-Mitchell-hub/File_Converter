# doc_converter

> 企业级文档转换工具 (Enterprise-grade document converter for Python)
>
> Excel / Word / PDF / 图片 / OCR 之间的多向转换，提供统一入口与可扩展插件架构。

---

## 项目介绍

`doc_converter` 是一个**纯 Python** 实现的统一文档转换工具，针对企业内部"格式分散、转换保真、批处理可控"的常见痛点：

- **统一入口**：`Converter.convert(src, dst)` 一行代码搞定；无需关心底层引擎。
- **可扩展**：基于 `Registry` + `BaseConverter` 抽象，新增一种转换只需写一个类并 `register`。
- **高保真**：Excel/Word → PDF 在 Windows 上优先使用本地 Office COM 接口（字体/颜色/图表/合并单元格全部保留）。
- **健壮**：单文件失败不影响批量任务；目标目录自动创建；同名文件不会覆盖原始。
- **可观测**：内置 logging，按 `[时间] [级别] [模块]` 输出到 stderr。

典型场景：

- 财务报表批量导出 PDF 用于归档；
- 扫描件（图片）OCR 识别后转 Excel；
- 把 PDF/Word 手册拆成高清 PNG 用于内嵌 PPT；
- 第三方数据交付前批量格式归一。

---

## 功能清单

| 编号 | 功能 | 方向 | 默认引擎 |
|------|------|------|----------|
| 1 | Excel → PDF | `.xlsx`/`.xls` → `.pdf` | Windows: `pywin32`；其它: `LibreOffice` |
| 2 | PDF → Excel | `.pdf` → `.xlsx` | `pdfplumber` + `openpyxl` |
| 3 | Excel → 图片 | `.xlsx`/`.xls` → `.png`/`.jpg` | `LibreOffice` + `PyMuPDF` (300 DPI) |
| 4 | PDF → 图片 | `.pdf` → `.png`/`.jpg` | `PyMuPDF` (300 DPI) |
| 5 | 图片 → PDF | `.png`/`.jpg`/`.jpeg`/`.bmp`/`.tiff`/`.webp` → `.pdf` | `Pillow` |
| 6 | Word → PDF | `.docx`/`.doc` → `.pdf` | Windows: `docx2pdf`/`pywin32`；其它: `LibreOffice` |
| 7 | PDF → Word | `.pdf` → `.docx` | `pdfplumber` + `python-docx`（仅文本） |
| 8 | 图片 OCR → Excel | `.png`/`.jpg`/... → `.xlsx` | `pytesseract` (Tesseract) |

合计 18+ 个支持组合，覆盖企业 90% 的"格式互换"诉求。

---

## 支持矩阵

| 输入 → 输出 | xlsx | xls | docx | doc | pdf | png | jpg | bmp/tiff/webp |
|-------------|:----:|:---:|:----:|:---:|:---:|:---:|:---:|:-------------:|
| **xlsx**    |  -   |  -  |  -   |  -  | ✅  | ✅  | ✅  |       -       |
| **xls**     |  -   |  -  |  -   |  -  | ✅  | ✅  | ✅  |       -       |
| **docx**    |  -   |  -  |  -   |  -  | ✅  |  -  |  -  |       -       |
| **doc**     |  -   |  -  |  -   |  -  | ✅  |  -  |  -  |       -       |
| **pdf**     |  ✅  |  -  |  ✅   |  -  |  -  | ✅  | ✅  |       -       |
| **png**     |  ✅  |  -  |  -   |  -  | ✅  |  -  |  -  |       -       |
| **jpg/jpeg**|  ✅  |  -  |  -   |  -  | ✅  |  -  |  -  |       -       |
| **bmp/tiff/webp** | ✅ | - | - | - | ✅ | - | - | - |

> 单元格为空表示暂不支持（可作为后续扩展方向，例如 Markdown → PDF、Word → 图片 等）。

---

## 安装指南

### 1) 基础 Python 依赖

```bash
# 1. 克隆 / 拷贝项目到本地
cd doc_converter

# 2. 推荐使用虚拟环境
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
.venv\Scripts\activate             # Windows

# 3. 安装基础依赖
pip install -r requirements.txt
```

### 2) 可选：OCR（图片 → Excel）

```bash
pip install pytesseract
```

还需要系统层安装 Tesseract 二进制：

| 平台 | 命令 |
|------|------|
| **Windows** | 前往 [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装包，安装时勾选 `Chinese (Simplified)` 语言包。 |
| **macOS** | `brew install tesseract tesseract-lang` |
| **Linux (Debian/Ubuntu)** | `sudo apt install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng` |

### 3) 可选：Windows + Microsoft Office（提升保真度）

```bash
pip install pywin32 docx2pdf
```

仅当本机已安装 Microsoft Office（Excel/Word）时有效。它能调用本机 Office 的 `ExportAsFixedFormat`，完整保留格式。

### 4) 可选：LibreOffice（跨平台降级方案）

| 平台 | 命令 |
|------|------|
| **Windows** | 前往 [libreoffice.org](https://www.libreoffice.org/download/download/) 下载安装。 |
| **macOS** | `brew install --cask libreoffice` |
| **Linux (Debian/Ubuntu)** | `sudo apt install libreoffice` |

> 在没有 MS Office 的 Linux/macOS/无 GUI 服务器上，**LibreOffice 是必装的**，否则 `.xlsx` → `.pdf`、`.docx` → `.pdf` 都会失败。

---

## 快速开始

```python
from doc_converter import Converter

# 1. Excel 转 PDF
Converter.convert("samples/report.xlsx", "output/report.pdf")

# 2. PDF 拆成多页 PNG（自动命名为 manual_page_001.png / 002.png...）
Converter.convert("samples/manual.pdf", "output/manual_page.png")

# 3. 图片合并成 PDF
Converter.convert("samples/photo.png", "output/photo.pdf")

# 4. 扫描件 OCR -> Excel
Converter.convert("samples/scan.png", "output/scan.xlsx")
```

更多场景见 [`examples/`](./examples/) 目录。

---

## 架构说明

```
doc_converter/
├── __init__.py              # 暴露 Converter / BatchProcessor / get_logger
├── core/
│   ├── base.py              # BaseConverter / ConversionError / ConversionResult
│   ├── converter.py         # 统一入口 Converter（门面模式）
│   ├── registry.py          # 全局路由表（线程安全）
│   ├── batch.py             # 目录级批处理 BatchProcessor
│   └── logger.py            # 日志配置 / set_level
├── converters/
│   ├── excel_converter.py   # Excel <-> PDF / Excel -> 图片
│   ├── pdf_converter.py     # PDF -> 图片 / PDF -> Excel
│   ├── image_converter.py   # 图片 -> PDF（支持多图合并）
│   ├── word_converter.py    # Word <-> PDF
│   └── ocr_converter.py     # 图片 OCR -> Excel
└── utils/
    ├── paths.py             # ensure_dir / unique_output_path / split_ext
    └── platform.py          # Platform / detect_platform / has_office / has_libreoffice
```

**设计模式**：

- **Facade（门面）**：`Converter` 对外只暴露 3 个方法（`convert` / `batch` / `supported`）。
- **Strategy（策略）**：每个具体 `*Converter` 是一种转换策略，可被 `Registry` 自由替换。
- **Registry（注册表）**：`(src_ext, dst_ext) -> [BaseConverter]` 的路由表。
- **Template Method（模板方法）**：`BaseConverter` 定义 `_resolve_paths` / `_check_pair_supported` 等公共骨架。

**数据流**：

```
Caller
  └─ Converter.convert(src, dst)
        ├─ 1) 参数校验（路径存在、扩展名合法）
        ├─ 2) Registry.resolve(src_ext, dst_ext)  -> 选转换器
        └─ 3) handler.convert(src, dst)
                └─ 4) 具体转换器按引擎能力选 soffice / win32 / fitz / ...
```

---

## API 参考

### `Converter.convert(source, target, *, overwrite=False, **kwargs)`

把单个文件从 `source` 转换为 `target`。

- **参数**
  - `source` (`str | Path`)：源文件路径。
  - `target` (`str | Path`)：目标文件路径（**必须带扩展名**）。
  - `overwrite` (`bool`)：目标存在时是否覆盖。默认 `False`（追加 `_1`、`_2` 后缀）。
  - `**kwargs`：透传给具体转换器（如 `dpi=200`、`lang="eng"`、`engine="libreoffice"`）。
- **返回**：实际写入的 `Path`。
- **抛出**：`ConversionError`（不支持的组合、源文件缺失、依赖缺失、引擎失败等）。

### `Converter.batch(source_dir, target_dir, *, overwrite=False, continue_on_error=True)`

目录级批量处理。详见 [`examples/batch_convert.py`](./examples/batch_convert.py)。

- **返回**：`list[ConversionResult]`，每个元素含 `source / target / success / message`。
- **`continue_on_error=True`** 时：单文件失败仅记录到 `message`，不中断其他任务。

### `Converter.supported() -> list[tuple[str, str]]`

返回当前已注册的所有支持组合，例如 `[(".xlsx", ".pdf"), (".pdf", ".png"), ...]`。

### `Converter.can_convert(source, target) -> bool`

轻量级"是否支持"判断（不触磁盘 IO，只看扩展名）。

### `BatchProcessor`（高级用法）

```python
from doc_converter import BatchProcessor

results = BatchProcessor(
    source_dir="input/",
    target_dir="output/",
    overwrite=False,
    continue_on_error=True,
    recursive=True,        # 默认 True，递归处理子目录
).run()
```

### `Registry`（扩展开发用）

```python
from doc_converter.core.registry import Registry
from doc_converter.core.base import BaseConverter

class MyConverter(BaseConverter):
    name = "MyConverter"
    supported_pairs = ((".foo", ".bar"),)
    def convert(self, source, target): ...

Registry.register(MyConverter())
```

---

## 示例

| 文件 | 说明 |
|------|------|
| [`examples/single_convert.py`](./examples/single_convert.py) | 6 个单文件转换场景：Excel/PDF/Word/图片/OCR |
| [`examples/batch_convert.py`](./examples/batch_convert.py) | 整目录批量转换 + 结果汇总 |
| [`examples/ocr_to_excel.py`](./examples/ocr_to_excel.py) | OCR 专项：自定义语言、置信度阈值 |

运行方式（在项目根目录）：

```bash
python examples/single_convert.py
python examples/batch_convert.py
python examples/ocr_to_excel.py
```

---

## 平台差异

| 平台 | Excel → PDF | Word → PDF | 备选 |
|------|-------------|------------|------|
| **Windows + MS Office** | `pywin32`（保真度最高） | `docx2pdf` / `pywin32` | 字体、图表、合并单元格 100% 保留 |
| **Windows + 无 Office** | `LibreOffice` | `LibreOffice` | 安装 LibreOffice 后即可 |
| **Linux 服务器** | `LibreOffice` | `LibreOffice` | 必装 `libreoffice` 包 |
| **macOS** | `LibreOffice` | `docx2pdf`（需 MS Word for Mac） | 推荐 `brew install --cask libreoffice` |

判断逻辑写在 [`doc_converter/utils/platform.py`](./doc_converter/utils/platform.py)，可通过 `office_status()` 编程查询。

---

## 大文件与内存优化建议

### 1) PDF 渲染（PDF → 图片 / Excel → 图片）

`PyMuPDF (fitz)` 本身就是**分页**加载的，按 `doc.load_page(i)` 取单页不会把整本 PDF 一次性读入内存。建议：

- 多页 PDF 转换时，**单页处理 + 立即写出**，不要把全部 page 累积到 list。
- 若 PDF 超过 1 GB，使用 `fitz.open(src, filetype="pdf")` 后**显式释放**：`del doc` / `doc.close()`。

### 2) Excel 大文件

- **读取**侧：若 `.xlsx` 很大且只需遍历数据，使用 `openpyxl.load_workbook(..., read_only=True)` 流式读取。
- **写入**侧：本项目 `PDF → XLSX` 走的是 `openpyxl.Workbook()`，对几十 MB 以内的 PDF 完全够用；超过 100 MB 时建议先在源头 PDF 上做拆分。
- 若需要 **OOXML 公式 / 样式** 还原，可考虑切换到 `xlsxwriter`，但本项目出于"读+写"对称性仍选用 `openpyxl`。

### 3) OCR 大图片

Tesseract 对超大图片（>4000×4000）效率与准确率都会下降。优化：

```python
from PIL import Image
img = Image.open("huge_scan.png")
# 等比缩放至最长边 2000
w, h = img.size
scale = 2000 / max(w, h)
img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
img.save("resized.png")
```

再对 `resized.png` 做 OCR。

### 4) 批量处理（`Converter.batch`）

- 单进程默认顺序处理；如需并发，可在外层用 `concurrent.futures.ProcessPoolExecutor` 调 `Converter.convert`。
- 注意 LibreOffice 同一时间只能跑一个实例；并发时建议加 `semaphore = threading.Semaphore(1)` 串行化 soffice 调用。
- 大目录建议**按扩展名分批**：先 PDF、再 Excel、最后 OCR，避免 Tesseract 内存占用相互挤兑。

### 5) 日志

转换时若开启 `logging.DEBUG`，日志会输出每一步路径/引擎信息。生产环境建议 `INFO`，debug 排错时再提高。

```python
import logging
from doc_converter.core.logger import set_level
set_level(logging.INFO)
```

---

## 扩展指南

加一个新的转换器只需 3 步：

### Step 1：继承 `BaseConverter`

```python
# doc_converter/converters/markdown_converter.py
from pathlib import Path
from typing import ClassVar, Tuple
from ..core.base import BaseConverter, ConversionError, PathLike

class MarkdownConverter(BaseConverter):
    name: ClassVar[str] = "MarkdownConverter"
    supported_pairs: ClassVar[Tuple[Tuple[str, str], ...]] = (
        (".md", ".pdf"),
        (".md", ".html"),
    )

    def convert(self, source: PathLike, target: PathLike, **kwargs) -> Path:
        src, dst = self._resolve_paths(source, target)
        # ... 你的实现 ...
        return dst
```

### Step 2：导出到包 `__init__`

```python
# doc_converter/converters/__init__.py
from .markdown_converter import MarkdownConverter   # 触发自动注册
```

### Step 3：（可选）手动注册

```python
from doc_converter.core.registry import Registry
from doc_converter.converters.markdown_converter import MarkdownConverter
Registry.register(MarkdownConverter())
```

注册后 `Converter.convert("README.md", "out.pdf")` 会自动路由到 `MarkdownConverter`。

---

## 已知限制

1. **PDF → Word 仅文本**：会丢失字体、颜色、表格、列、页眉页脚、矢量图等版式信息；只适合"纯文字可编辑化"场景。
2. **PDF → Excel 复杂表格格式丢失**：只能识别明显的文本边框表格；扫描版 PDF 的表格需要先 OCR 再解析。
3. **OCR 复杂排版按行还原**：仅按 `block_num / par_num / line_num` 还原为"行 × 列"，不识别表格线、单元格合并、字体粗细。
4. **LibreOffice 转换依赖系统二进制**：在精简 Docker 镜像（无 `soffice`）上不可用，需要安装 `libreoffice` 包。
5. **`pywin32` 仅 Windows** + **本机已装 Office**：其它平台会自动回退到 LibreOffice。
6. **目标必须带扩展名**：传目录或不带后缀会抛 `ConversionError`（避免歧义导致用户预期外行为）。

---

## License

MIT License

Copyright (c) 2026 doc_converter contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
