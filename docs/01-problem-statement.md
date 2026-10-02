# 1. Bản mô tả bài toán & Vấn đề thực tế cần giải quyết

## Tên bài toán
**ReqCheck** — Trợ lý AI rà soát tài liệu yêu cầu phần mềm và sinh danh sách Acceptance Criteria (Given/When/Then) để con người duyệt.

## Vấn đề thực tế
Sinh viên IT làm đồ án nhóm, hoặc lập trình viên mới vào nghề, thường nhận **đề bài / yêu cầu viết sơ sài** (từ giảng viên, khách hàng, hoặc trưởng nhóm). Trước khi code, họ phải tự:

1. Đọc và tách tài liệu thành từng yêu cầu riêng lẻ.
2. Tìm chỗ **thiếu** thông tin, chỗ **mơ hồ** ("nhanh", "dễ dùng"), chỗ **mâu thuẫn**, chỗ **vô lý**.
3. Hỏi lại người ra đề để làm rõ.
4. Viết tiêu chí nghiệm thu (Acceptance Criteria) cho từng yêu cầu, gồm cả ca thường, ca biên và ca lỗi.
5. Nhập vào Jira/Trello/checklist nhóm.

**Nút thắt cổ chai** nằm ở bước 2 và 4: rất dễ **sót ràng buộc** (đọc lướt), và dễ viết tiêu chí chỉ cho trường hợp đẹp (happy path). Sót ở giai đoạn này thì đến lúc demo/nộp bài mới phát hiện, phải làm lại.

## Mô tả bài toán (theo mẫu thầy/cô yêu cầu)
| Mục | Nội dung |
|---|---|
| **User** (người bấm nút mỗi ngày) | Sinh viên IT làm đồ án nhóm; lập trình viên/QA mới vào nghề. |
| **Input** | Tài liệu yêu cầu dạng văn bản (dán vào hoặc file `.txt`), tối đa 2000 từ, kèm 1 câu chỉ thị của người dùng. |
| **Output** | Một file **JSON** đúng schema: `status`, `questions`, `requirements`, `acceptance_criteria`, `warnings` (kèm bản Markdown/checklist để người duyệt đọc). |
| **Workflow thủ công hiện tại** | Đọc → tách yêu cầu → tìm chỗ thiếu/mơ hồ/mâu thuẫn → hỏi lại → viết AC → nhập Jira/Trello. |
| **Value AI tạo ra** | (1) Giảm thời gian từ tài liệu thô đến checklist AC. (2) Giảm số ràng buộc bị bỏ sót, nhờ luôn phải trích dẫn nguyên văn và luôn dừng lại hỏi khi thiếu/mơ hồ/mâu thuẫn. |
| **Kiểm thử (đúng/sai rõ ràng)** | Chấm bằng code: JSON hợp lệ; trích dẫn có thật trong tài liệu; không có số liệu bịa; mỗi yêu cầu có AC; từ chối đúng lúc. Xem `evals/`. |
| **Scope V1** | Tài liệu văn bản → JSON (+ Markdown). Không tích hợp Jira, không đọc file/URL ngoài, không sinh code. |

## Kiểm tra tính khả thi (Feasibility Checklist — 7 câu hỏi)
| Tiêu chí | Câu trả lời của ReqCheck | Red flag? |
|---|---|---|
| Người dùng | Sinh viên IT / dev-QA mới: người thực sự nhận đề bài mơ hồ hằng tuần. | Không |
| Đầu vào | Văn bản yêu cầu có sẵn, người dùng tự dán; giới hạn 2000 từ. | Không |
| Đầu ra | JSON có schema cố định, kiểm tra được bằng code. | Không |
| Quy trình | Người viết đã tự làm thủ công quy trình 5 bước trên cho đồ án của mình. | Không |
| Giá trị | Đo được độ tin cậy qua 10 kịch bản (số ca đạt/trượt). Thời gian tiết kiệm: chưa đo. | Không |
| Kiểm thử | Có tiêu chí đúng/sai rõ ràng cho từng kịch bản (xem `evals/checks.py`). | Không |
| Phạm vi | V1 chỉ là 1 system prompt + 3 file code ngắn, dựng được trong 15–20 phút. | Không |

## Cách đo giá trị trong bài này
Giá trị được đo bằng **độ tin cậy của hành vi**, không phải bằng thời gian tiết kiệm:
- Số kịch bản thử lửa đạt trên 10 ca (V1 4/10 → V2 9/10, cùng model, xem `docs/comparison-v1-v2.md`).
- Số lỗi nghiêm trọng bị chặn: sinh tiêu chí trên dữ liệu mâu thuẫn/vô lý, làm theo lệnh chèn, xử lý tài liệu quá dài.

**Chưa đo:** thời gian tiết kiệm so với làm thủ công. Bài này không đưa ra con số tiết kiệm thời gian vì chưa có phép đo thật.
