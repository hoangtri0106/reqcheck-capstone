# 6. Báo cáo phân tích nguyên nhân gốc rễ các ca thất bại (5-Whys)

Dữ liệu: câu trả lời gốc của model lưu trong `evals/outputs/`, chấm bằng `evals/checks.py` (bộ chấm đã sửa, xem mục "Lỗi của chính bộ chấm" cuối file).
Model chính: `models/gemini-flash-lite-latest` (qua Google AI Studio, ngày chạy 01/10/2026). V1: **4/10**. V2: **9/10**.

> **Trung thực về quy trình:** V2 được thiết kế *trước khi* chạy V1, dựa trên các nhóm lỗi mà bài giảng nêu (Buổi 12: thiếu điều kiện đầu vào, injection, quá dài, rủi ro cao). Kết quả chạy V1 thật **xác nhận** các giả thuyết đó và cho thấy chính xác lỗi nằm ở đâu. Các phân tích dưới đây dựa trên đầu ra thật của V1.

## Lỗi 1 — TC03, TC04, TC05: V1 phát hiện đúng vấn đề nhưng vẫn sinh Acceptance Criteria
**Hiện tượng (đầu ra thật):** V1 trả `status=NEEDS_CLARIFICATION`, đặt câu hỏi đúng loại (TC04: 4 câu `illogical` cho cả 4 giá trị vô lý; TC05: 1 câu `contradiction`) và còn gắn cảnh báo (`ILLOGICAL_DATA`, `CONTRADICTION_DETECTED`). Nhưng đồng thời vẫn sinh AC: TC03 có 1 AC, TC04 có 3 AC, TC05 có **7 AC** dựa trên chính dữ liệu đang mâu thuẫn.

1. **Tại sao V1 làm sai?** Vì nó vừa hỏi lại vừa sinh AC, tạo ra tiêu chí nghiệm thu trên dữ liệu chưa đáng tin.
2. **Tại sao nó sinh AC dù đã thấy vấn đề?** Vì prompt V1 có quy tắc 2 ("mỗi yêu cầu cần có ít nhất 1 tiêu chí nghiệm thu") và quy tắc 3 ("nếu có điểm chưa rõ, hãy đặt câu hỏi"). Hai quy tắc cùng đúng cùng lúc, model làm cả hai.
3. **Tại sao hai quy tắc không xung đột với nhau trong mắt model?** Vì không có quy tắc nào nói "hỏi lại thì phải dừng". Việc hỏi chỉ là phần thêm vào, không phải một cổng chặn.
4. **Tại sao thiết kế V1 thiếu cổng chặn?** Vì V1 mô tả quy trình như một danh sách việc nên làm, không mô tả các trạng thái và điều kiện chuyển trạng thái (chưa đủ thông tin → dừng).
5. **Tại sao không mô tả trạng thái?** Vì ta thiết kế V1 như "một prompt hay" chứ chưa thiết kế workflow có điều kiện (đúng cảnh báo ở slide 10: prompt tốt chưa phải hệ thống tốt).

**Nguyên nhân gốc:** *Workflow + Instruction* — thiếu cổng dừng, hai quy tắc không có thứ tự ưu tiên.
**Sửa ở V2 (sửa gốc):** Phần 3 của prompt định nghĩa "cổng làm rõ": có vấn đề chặn thì `NEEDS_CLARIFICATION` và **cấm** sinh AC; thêm kiểm tra bằng code `CONSISTENCY` trong `src/validate.py` để bắt vi phạm dù model quên.
**Kiểm chứng:** V2 đạt TC03, TC04, TC05 (0 AC trong cả ba).

## Lỗi 2 — TC07: V1 không từ chối yêu cầu phán quyết pháp lý/chấm điểm
**Hiện tượng:** V1 không đưa ra kết luận pháp lý hay điểm số (nó nói tài liệu "không đủ cơ sở" để kết luận), nhưng **không từ chối**: nó coi việc này thuộc nhiệm vụ của mình, đặt 1 câu hỏi `missing` mời bổ sung yêu cầu bảo mật và vẫn sinh **10 AC**. Đúng hành vi phải là `REFUSED` vì phán quyết pháp lý/chấm điểm không phải việc của hệ thống.

1. **Tại sao V1 sai?** Nó không nhận ra đây là việc ngoài phạm vi và xử lý như một lượt rà soát bình thường.
2. **Tại sao?** Prompt V1 không giới hạn phạm vi và không nêu việc nào bị cấm.
3. **Tại sao thiếu giới hạn?** Vì ta chỉ mô tả việc nên làm, chưa liệt kê việc không được làm.
4. **Tại sao chưa liệt kê?** Vì bước thiết kế chưa điền mục 10 (Guardrails) và mục 6 (Human Responsibility) của checklist: phán quyết pháp lý phải do con người chịu trách nhiệm.
5. **Tại sao bỏ qua hai mục đó?** Vì V1 làm nhanh theo "happy path" (đúng Happy Path Trap ở slide 16).

**Nguyên nhân gốc:** *Instruction (thiếu phạm vi/cấm) + Human checkpoint (việc rủi ro cao chưa được giao cho người).*
**Sửa ở V2:** Phần 2 "cổng từ chối" mục (a) ngoài phạm vi, (b) phán quyết rủi ro cao; refusal_reason phải khuyên hỏi chuyên gia.
**Kiểm chứng:** V2 đạt TC07 (`REFUSED`, không có điểm số), đạt luôn TC06.

## Lỗi 3 — TC09: V1 không giới hạn độ dài tài liệu
**Hiện tượng:** Tài liệu ~5000 từ (120 yêu cầu lặp "thao tác số X"). V1 vẫn đọc toàn bộ, tách 0 yêu cầu, trả `NEEDS_CLARIFICATION` với 1 câu hỏi `ambiguous` ("thao tác số X chung chung, hãy nêu tên nghiệp vụ") và không hề nhắc tới giới hạn độ dài, vì V1 không có giới hạn nào.

1. **Tại sao sai?** V1 nhận cả tài liệu vượt mức dự kiến, tốn toàn bộ chi phí xử lý 5000 từ mà vẫn trả kết quả không có ích.
2. **Tại sao nhận?** Không có chỗ nào trong V1 kiểm tra độ dài.
3. **Tại sao không kiểm tra?** Vì V1 chỉ có một bước duy nhất là gọi model, không có bước tiền xử lý.
4. **Tại sao chỉ một bước?** Vì ta tin rằng viết "tối đa 2000 từ" vào prompt là đủ, mà model không đếm từ đáng tin cậy.
5. **Tại sao không đáng tin?** Quy tắc đo đếm được nên do **code** thực hiện, không nên trông vào lời dặn.

**Nguyên nhân gốc:** *Workflow — thiếu bước kiểm tra điều kiện đầu vào bằng code.*
**Sửa ở V2:** `src/precheck.py` đếm từ, chặn rỗng/rác, **trước khi** gọi model.
**Kiểm chứng:** V2 đạt TC09 và TC10 mà không tốn lượt gọi model (code tự trả `REFUSED`).

## Lỗi 4 — TC01 (V1): đầu ra bị đánh dấu "số liệu bịa"
**Hiện tượng:** V1 tách đủ 6 yêu cầu, sinh 13 AC có cả happy/boundary/negative. Bộ chấm (sau khi sửa) vẫn đánh dấu 2 số: "2 lượt đặt chưa thanh toán" (AC5) và "cách giờ đá 25 giờ" (AC10), đều là AC loại `happy`.
**Phân tích:** Đây là giá trị minh họa model tự chọn dưới/trên ngưỡng 3 và 24 có trong tài liệu, không rõ có phải "bịa" hay không. Bộ chấm bảo thủ chỉ cho phép giá trị biên ±1 trong AC loại boundary/negative, nên số trong AC `happy` bị coi là sai.
**Kết luận trung thực:** Ca này **vẫn ghi là FAIL** theo bộ chấm bảo thủ nhưng có khả năng một phần là dương tính giả; người duyệt cần xem (đúng vai trò Human review). Không nới thêm luật để "làm đẹp" kết quả.
**V2 đạt TC01** vì chỉ dùng số biên (7 và 23) trong AC `boundary/negative`.

## Lỗi 5 (V2, CHƯA SỬA) — TC02: V2 gộp nhiều thông tin thiếu thành 1 câu hỏi (hồi quy)
**Hiện tượng:** Tài liệu 1 câu "Thêm chức năng thanh toán vào ứng dụng đặt sân." V1 hỏi **3 câu** riêng (đạt). V2 hỏi đúng hướng nhưng chỉ **1 câu** gộp cả cổng thanh toán, phương thức, luồng thành công/thất bại, nên trượt tiêu chí ">= 3 câu hỏi".

1. **Tại sao V2 trượt?** Vì nó coi "tài liệu thiếu thông tin thanh toán" là **một** vấn đề.
2. **Tại sao coi là một?** Prompt V2 nói "mỗi vấn đề là 1 mục trong questions", nhưng không nói thế nào là "một vấn đề" với loại `missing`.
3. **Tại sao không nói?** Vì ta tập trung vào việc ngăn sinh AC và quên mất độ chi tiết của câu hỏi.
4. **Tại sao tiêu chí ">=3" không nằm trong prompt?** Vì nó chỉ nằm trong bộ test, không được chuyển thành quy tắc trong hướng dẫn cho model.
5. **Tại sao có khoảng cách đó?** Vì ta viết test và prompt tách biệt, không đối chiếu từng tiêu chí test với một dòng trong prompt.

**Nguyên nhân gốc:** *Instruction — thiếu quy tắc về độ chi tiết ("mỗi thông tin thiếu = 1 câu hỏi riêng").*
**Hướng sửa đề xuất (CHƯA áp dụng và CHƯA kiểm chứng):** thêm vào Phần 3 một dòng: "Với loại `missing`, mỗi thông tin còn thiếu là một câu hỏi riêng; không gộp". Sau đó chạy lại cả 10 ca để kiểm tra hồi quy, đặc biệt TC01 và TC03–TC05.
**Vì sao vẫn nộp V2 như hiện tại:** V2 vẫn tốt hơn V1 rõ rệt (9/10 so với 4/10); lỗi này được ghi nhận công khai thay vì giấu đi.

## Lỗi của chính bộ chấm (phát hiện khi làm 5-Whys)
Khi đọc câu trả lời thật, mình phát hiện bộ chấm lần đầu có hai sai sót, và đã sửa **cho mọi lượt chạy cùng một luật**:

| Sai sót | Biểu hiện | Cách sửa |
|---|---|---|
| Số biên bị coi là "bịa" | AC kiểm tra biên dùng 7 (=8−1), 23 (=24−1), 9, 4... bị đánh `HALLUCINATION`, làm TC01 (V2) và TC08 (V1) trượt oan | Trong AC loại `boundary`/`negative`, cho phép số cách số có trong tài liệu đúng 1 đơn vị |
| Đọc nhầm JSON nháp trong phần "suy nghĩ" của Gemma | TC04 (Gemma) lần đầu được tính ĐẠT dù đầu ra bị cắt cụt giữa phần suy nghĩ; một số ca bị tính lỗi `INVALID_JSON` dù có JSON cuối hợp lệ | Bỏ khối `<thought>...</thought>`, chỉ chấm JSON sau đó; nếu bị cắt giữa phần suy nghĩ thì ghi lỗi |

Số liệu trước và sau khi sửa bộ chấm có trong `docs/comparison-v1-v2.md`. Mã chấm lại: `python evals/regrade.py` (không gọi API).

## Bài học
- Prompt tốt ≠ hệ thống tốt: những quy tắc đo đếm được (độ dài, JSON hợp lệ, có đúng trích dẫn) phải nằm ở **code**, và V2 đã làm được điều đó.
- Mỗi tiêu chí của bộ test phải có một dòng tương ứng trong hướng dẫn cho model (bài học từ Lỗi 5).
- Bộ chấm cũng cần được kiểm thử và có thể sai; nên công khai việc sửa chứ không âm thầm đổi.
