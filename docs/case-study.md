# 12. Case Study — ReqCheck: trợ lý AI rà soát yêu cầu phần mềm, có bằng chứng kiểm thử

**Situation.** Sinh viên IT thường nhận đề bài đồ án sơ sài. Tách yêu cầu, tìm chỗ thiếu/mơ hồ/mâu thuẫn và viết tiêu chí nghiệm thu bằng tay vừa tốn công vừa dễ sót ràng buộc.

**Task.** Xây dựng một AI Assistant (Level 2, workflow có cổng kiểm duyệt) đọc tài liệu yêu cầu và sinh Acceptance Criteria Given/When/Then, với ba ràng buộc cứng: không bịa số liệu, dừng lại hỏi khi thiếu/mơ hồ/mâu thuẫn, từ chối việc ngoài phạm vi.

**Action.**
- Thiết kế theo checklist 11 thành phần; AI chỉ có quyền đọc; con người duyệt trước khi đưa vào Jira/Trello.
- Tách kiến trúc: `precheck` (code) → model → `validate` (code) → người duyệt; model chỉ nằm sau một adapter.
- Xây bộ Evals 10 kịch bản chấm bằng code (trích dẫn nguyên văn, số liệu bịa, độ phủ, từ chối đúng lúc).
- Chạy V1 trên model thật, phân tích 5-Whys từ đầu ra thật, rồi đối chiếu với V2 trên cùng model.
- Chạy Model Swap Test sang một dòng model khác (Gemma) và ghi lại chi phí thật của việc đổi model.

**Result (số liệu thật, ngày chạy 01/10/2026, Google AI Studio).**
- Độ tin cậy trên 10 kịch bản, cùng model `gemini-flash-lite-latest`: **V1 4/10 → V2 9/10**.
- V2 bắt được cả ba nhóm lỗi nghiêm trọng của V1: sinh tiêu chí trên dữ liệu mâu thuẫn/vô lý (TC03–TC05), không từ chối phán quyết pháp lý (TC07), không giới hạn tài liệu quá dài (TC09, nay do code chặn, không tốn lượt gọi model).
- Model Swap: V2 đạt 9/10 trên Gemini Flash-Lite và 6/10 trên Gemma 4 26B; 3 ca trượt của Gemma là đầu ra bị cắt cụt do model viết phần suy nghĩ vào đầu ra.
- Còn tồn tại (công khai): TC02 hồi quy ở V2 (gộp nhiều thông tin thiếu vào 1 câu hỏi); chưa đo thời gian tiết kiệm.

**Bài học.**
1. Prompt tốt chưa phải hệ thống tốt: quy tắc đo đếm được (độ dài, JSON hợp lệ, trích dẫn có thật) nên do code đảm nhiệm. Hai ca của V2 đạt 100% nhờ code, không nhờ model.
2. Mỗi tiêu chí của bộ test phải có một dòng tương ứng trong hướng dẫn cho model (nguyên nhân của hồi quy TC02).
3. Bộ chấm cũng có thể sai. Mình phát hiện bộ chấm đánh nhầm số biên là "bịa" và đọc nhầm JSON nháp của Gemma, nên đã sửa và chấm lại toàn bộ bằng cùng một luật, ghi lại số trước và sau khi sửa thay vì âm thầm đổi.
4. Đổi model không chỉ là đổi tham số: phải xử lý định dạng đầu ra riêng của từng model.

Repo: [[ĐIỀN: link GitHub]] · Trang trải nghiệm: [[ĐIỀN: link GitHub Pages]]
