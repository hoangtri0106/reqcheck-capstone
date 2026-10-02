# ReqCheck — Trợ lý AI rà soát yêu cầu phần mềm & sinh Acceptance Criteria

> Bài tập cuối khóa: *Trí tuệ Nhân tạo Ứng dụng & Kỹ năng Kỹ sư Kỷ nguyên mới* (Buổi 12).
> Tác giả: [[ĐIỀN: họ tên — MSSV]]

**ReqCheck** đọc một tài liệu yêu cầu phần mềm sơ sài và trả về JSON gồm: các yêu cầu đã tách, **câu hỏi làm rõ** (thiếu / mơ hồ / mâu thuẫn / phi logic), và **Acceptance Criteria** dạng Given/When/Then để con người duyệt.

Điểm khác với "một prompt hay": luồng xử lý có **cổng chặn bằng code ở cả đầu vào lẫn đầu ra**, AI chỉ có quyền đọc, và mọi kết luận đều được kiểm chứng bằng **bộ 10 kịch bản thử lửa** chấm tự động.

```
Người dùng ─► PRECHECK (code) ─► MODEL (read-only) ─► VALIDATE (code) ─► NGƯỜI DUYỆT ─► Jira/Trello
               rỗng/rác/dài/injection   prompt V2          schema·trích dẫn·số liệu
```
Sơ đồ đầy đủ: [`docs/workflow-diagram.png`](docs/workflow-diagram.png)

## Kết quả thật (chạy ngày 01/10/2026, Google AI Studio)
| Phiên bản | Model | Đạt / 10 kịch bản |
|---|---|---|
| V1 | `gemini-flash-lite-latest` | **4/10** |
| V2 | `gemini-flash-lite-latest` (cùng model) | **9/10** |
| V2 (Model Swap) | `gemma-4-26b-a4b-it` | **6/10** |

Số liệu là kết quả sau khi sửa bộ chấm (chấm lần đầu: 3, 8, 5). Việc sửa, lý do và số trước/sau được ghi đầy đủ trong [`docs/comparison-v1-v2.md`](docs/comparison-v1-v2.md). Còn một hồi quy chưa sửa (TC02) được công khai trong [`evals/failure-analysis.md`](evals/failure-analysis.md).

**Trải nghiệm trực tiếp:** [[ĐIỀN: https://<tên-github>.github.io/reqcheck-capstone/]] (trang xem câu trả lời gốc của từng model và thử lớp kiểm tra đầu vào; bật GitHub Pages: Settings → Pages → Branch `main`, thư mục `/docs`).

## Cấu trúc repo
```
reqcheck-capstone/
├── README.md
├── docs/
│   ├── 01-problem-statement.md      # (1) Bài toán & vấn đề thực tế
│   ├── system-design.md             # (2) Thiết kế 11 thành phần
│   ├── workflow-diagram.png         #     Sơ đồ phân công AI – Con người (nguồn: workflow.dot)
│   ├── results-v1.md                # (5) Bảng kết quả thực tế V1
│   ├── comparison-v1-v2.md          # (8) Bảng đối chiếu V1↔V2
│   ├── model-swap-log.md            # (9) Nhật ký Model Swap Test
│   ├── index.html                   # (11) Trang trải nghiệm (GitHub Pages)
│   ├── qa-phan-bien.md              #      Chuẩn bị 5 câu phản biện
│   ├── limitations-safety.md        # (10) Hướng dẫn dùng, giới hạn, khuyến cáo an toàn
│   └── case-study.md                # (12) Bài Case Study cho GitHub/LinkedIn
├── instructions/
│   ├── system-prompt-v1.md          # (3) Prototype V1
│   └── system-prompt-v2.md          # (7) Prototype V2 (sau khi gỡ lỗi)
├── src/
│   ├── precheck.py                  # Lớp 1: chặn rỗng/rác/quá dài, gắn cờ injection
│   ├── validate.py                  # Lớp 4: schema, trích dẫn, số liệu bịa, độ phủ
│   ├── llm_adapter.py               # Model Adapter (chỗ duy nhất biết tên model)
│   └── pipeline.py                  # Điều phối + CLI + audit log
├── evals/
│   ├── test-cases.csv               # (4) Bộ 10 kịch bản thử lửa
│   ├── checks.py                    #     Tiêu chí đạt/trượt bằng code
│   ├── run_evals.py                 #     prepare / run / score / compare
│   ├── regrade.py                   #     Chấm lại đầu ra đã lưu (không gọi API)
│   ├── outputs/                     #     Câu trả lời THẬT của model (bằng chứng)
│   ├── results/                     #     Kết quả từng lượt chạy (.json/.md)
│   └── failure-analysis.md          # (6) 5-Whys
├── demo/
│   └── sample-inputs/               #     Dữ liệu mẫu cho 10 kịch bản
└── tests/test_grader.py             # Kiểm thử chính bộ chấm điểm
```

## Chạy nhanh
Yêu cầu: Python 3.9+, **không cần cài thêm thư viện**.

```bash
python tests/test_grader.py          # kiểm tra bộ chấm điểm (không cần API key)
```

### Chạy eval tự động (có API key)
```bash
export ANTHROPIC_API_KEY=...         # hoặc LLM_API_KEY nếu dùng --provider openai
python evals/run_evals.py run --version v1 --provider anthropic --model <tên-model>
python evals/run_evals.py run --version v2 --provider anthropic --model <tên-model>
python evals/run_evals.py compare --v1 v1__<tên-model> --v2 v2__<tên-model>
python evals/regrade.py     # chấm lại toàn bộ đầu ra đã lưu, không gọi API
```
Thêm `--max-tokens 8000` nếu model hay bị cắt cụt. Tên chạy lấy từ `--model` (dấu `/` đổi thành `-`).

### Chạy eval thủ công (dùng chatbot, không cần API key)
```bash
python evals/run_evals.py prepare --version v1 --model chatbot-A
```
Lệnh này tạo `evals/outputs/v1__chatbot-A/TC01.input.txt`, `TC02.input.txt`, ... Với **mỗi kịch bản**:
1. Mở **cuộc trò chuyện mới** (để các ca không ảnh hưởng nhau), dán `instructions/system-prompt-v1.md` làm system prompt.
2. Dán nội dung `TCxx.input.txt` và gửi.
3. Lưu **nguyên văn** câu trả lời vào `evals/outputs/v1__chatbot-A/TCxx.txt`.

Rồi chấm điểm: `python evals/run_evals.py score --version v1 --model chatbot-A`. Làm tương tự với `--version v2` (các ca TC09, TC10 do code tự chặn nên không cần chạy model).

### Dùng thực tế
```bash
python src/pipeline.py --version v2 --provider anthropic --model <tên-model> --input <file.txt>
```
Xem [`docs/limitations-safety.md`](docs/limitations-safety.md).

## Giới hạn
Chỉ văn bản ≤ 2000 từ; kiểm tra số liệu/injection bằng quy tắc, chưa hiểu ngữ nghĩa; bộ 10 kịch bản là bộ nhỏ. Xem đầy đủ trong tài liệu an toàn.
