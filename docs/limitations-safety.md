# 10. Hướng dẫn sử dụng, giới hạn và khuyến cáo an toàn

## Hướng dẫn sử dụng

### Cách 1 — Dùng qua chatbot (không cần code, không cần API key)
1. Mở chatbot bạn dùng (Claude, ChatGPT, Gemini, DeepSeek...). Tạo cuộc trò chuyện mới.
2. Dán toàn bộ nội dung `instructions/system-prompt-v2.md` làm **system prompt** (hoặc làm tin nhắn đầu tiên nếu chatbot không có ô system prompt).
3. Gửi tin nhắn theo đúng mẫu:
   ```
   <user_instruction>
   Phân tích tài liệu yêu cầu này và tạo Acceptance Criteria.
   </user_instruction>
   <document>
   ...dán tài liệu yêu cầu của bạn (≤ 2000 từ)...
   </document>
   ```
4. Đọc JSON trả về. Nếu `status` là `NEEDS_CLARIFICATION`: trả lời các câu hỏi rồi cập nhật tài liệu và chạy lại. Nếu `OK`: **duyệt từng AC** trước khi dùng.

> Cách 1 không có lớp precheck/validate bằng code. Hãy tự kiểm tra: giới hạn 2000 từ, trích dẫn có thật trong tài liệu, không có số liệu lạ.

### Cách 2 — Chạy đầy đủ workflow bằng dòng lệnh (có precheck + validate + log)
```bash
# Cần Python 3.9+, không cần cài thêm thư viện
export ANTHROPIC_API_KEY=...           # hoặc LLM_API_KEY cho provider "openai"
python src/pipeline.py --version v2 --provider anthropic --model <tên-model> \
       --input demo/sample-inputs/tc01_happy_path.txt --format md
```
Hoặc xem kết quả thử nghiệm thật trên trang trải nghiệm: `docs/index.html` (bật GitHub Pages, xem README).
Với API tương thích OpenAI (OpenAI, DeepSeek, Gemini...): `--provider openai --base-url <url> --model <tên-model>` (xem tài liệu nhà cung cấp để lấy base-url và tên model).

## Giới hạn đã biết
- Chỉ nhận **văn bản thuần**, tối đa **2000 từ**. Không đọc PDF/ảnh/URL.
- V2 **thận trọng có chủ đích**: gặp điểm chặn (thiếu, mơ hồ, mâu thuẫn, phi logic) là dừng và hỏi, không sinh AC một phần. Người dùng có thể thấy đôi lúc bị hỏi nhiều.
- Phép kiểm tra số liệu bằng code chỉ bắt được số **không xuất hiện** trong tài liệu; chưa hiểu nghĩa (một số đúng nhưng đặt sai chỗ vẫn lọt).
- Quét prompt injection bằng mẫu regex chỉ bắt được các cách diễn đạt phổ biến (tiếng Việt/Anh). Kẻ tấn công diễn đạt khác có thể qua mặt lớp này; khi đó chỉ còn Lớp 2 (prompt) và người duyệt.
- Kết quả phụ thuộc model. Chất lượng khác nhau giữa các model (xem `model-swap-log.md`).
- **Lỗi đã biết, chưa sửa (V2):** với tài liệu rất ngắn, V2 có thể gộp nhiều thông tin thiếu vào 1 câu hỏi thay vì tách riêng (TC02, xem `evals/failure-analysis.md`, Lỗi 5).
- Bộ chấm số liệu chỉ cho phép giá trị biên ±1 trong AC loại boundary/negative; số minh họa khác có thể bị đánh dấu nhầm. Người duyệt phải đọc, không tin tuyệt đối vào chữ PASS/FAIL.
- Một số model (ví dụ Gemma trong thử nghiệm) viết cả phần \"suy nghĩ\" vào đầu ra và có thể bị cắt cụt nếu `max_tokens` thấp; dùng `--max-tokens` lớn hơn.
- Chưa đo thời gian tiết kiệm và chưa đo chi phí/độ trễ.
- Chưa đánh giá trên tài liệu tiếng Anh hay tài liệu thật nhiều trang; bộ 10 kịch bản là bộ nhỏ, không đại diện cho mọi tình huống.

## Khuyến cáo an toàn
1. **AI chỉ đề xuất, người chịu trách nhiệm.** Không đưa AC vào Jira/Trello/hợp đồng khi chưa đọc.
2. **Không dán dữ liệu nhạy cảm** (thông tin cá nhân, bí mật khách hàng, mật khẩu, khóa API) vào tài liệu gửi cho model bên thứ ba.
3. **Không coi "AI báo đã kiểm tra" là bằng chứng.** Bằng chứng là kết quả của `validate.py` và của người duyệt.
4. **Không dùng ReqCheck để ra quyết định pháp lý, tuân thủ hay chấm điểm** (hệ thống được thiết kế để từ chối).
5. Nếu thấy cảnh báo `PROMPT_INJECTION` hoặc `VALIDATION FAILED`, hãy xem lại tài liệu gốc trước khi tin bất kỳ kết quả nào.
6. Không commit khóa API lên GitHub (`.env` đã nằm trong `.gitignore`).

## Rủi ro lớn nhất và trách nhiệm
Rủi ro lớn nhất: người dùng tin AC do AI sinh ra mà không duyệt, dẫn tới làm sai yêu cầu. Trách nhiệm cuối cùng thuộc về **người duyệt và đưa AC vào dự án**, không thuộc về AI.
