"""Lớp 1 - Input Sanitization (chạy bằng CODE, không phụ thuộc model).

Việc của file này:
  1. Chuẩn hóa Unicode, loại ký tự ẩn (zero-width) hay bị dùng để giấu câu lệnh.
  2. Chặn đầu vào rỗng / toàn ký tự rác.
  3. Chặn tài liệu vượt giới hạn độ dài.
  4. Gắn cờ (KHÔNG chặn) đoạn văn giống prompt injection.
Lý do làm bằng code: quy tắc "tối đa 2000 từ" viết trong prompt có thể bị model quên/bỏ qua,
còn code thì không.
"""
import json
import re
import unicodedata

MAX_WORDS = 2000
MIN_LETTERS = 20

ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u200e\u200f\u2060\ufeff"), None)

INJECTION_PATTERNS = [
    r"bỏ\s*qua\s+(mọi|tất cả|các|toàn bộ)?\s*(hướng dẫn|chỉ dẫn|quy tắc|lệnh|câu lệnh|chỉ thị)",
    r"quên\s+(mọi|tất cả|các|toàn bộ)?\s*(hướng dẫn|chỉ dẫn|quy tắc|lệnh|câu lệnh|chỉ thị)",
    r"mặc\s*kệ\s+.{0,60}(system\s*prompt|hướng dẫn|câu lệnh|quy tắc)",
    r"chỉ\s+(trả lời|in ra|xuất)\s+(đúng\s+)?(một|1)\s+từ",
    r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above)\s+(instructions|rules|prompts?)",
    r"disregard\s+.{0,40}instructions",
    r"you\s+are\s+now\s+",
    r"</?\s*(document|user_instruction|system)\s*>",
]


class PreCheck:
    def __init__(self):
        self.refuse = False
        self.code = None
        self.reason = None
        self.clean_text = ""
        self.flags = []          # list[dict(code, message)]

    def refusal_output(self):
        return {
            "status": "REFUSED",
            "refusal_reason": self.reason,
            "questions": [],
            "requirements": [],
            "acceptance_criteria": [],
            "warnings": [{"code": self.code, "message": self.reason}],
        }


def precheck(document: str) -> PreCheck:
    pc = PreCheck()
    text = unicodedata.normalize("NFC", document or "")
    hidden = len(text) - len(text.translate(ZERO_WIDTH))
    text = text.translate(ZERO_WIDTH)
    if hidden:
        pc.flags.append({"code": "HIDDEN_CHARS",
                         "message": f"Đã loại {hidden} ký tự ẩn (zero-width) khỏi tài liệu."})

    letters = sum(1 for ch in text if unicodedata.category(ch).startswith("L"))
    if letters < MIN_LETTERS:
        pc.refuse, pc.code = True, "EMPTY_OR_GARBAGE"
        pc.reason = ("Tài liệu rỗng hoặc gần như không có chữ, không có nội dung yêu cầu "
                     "để phân tích. Vui lòng cung cấp tài liệu yêu cầu dạng văn bản.")
        return pc

    words = len(text.split())
    if words > MAX_WORDS:
        pc.refuse, pc.code = True, "TOO_LONG"
        pc.reason = (f"Tài liệu dài {words} từ, vượt giới hạn {MAX_WORDS} từ. "
                     f"Vui lòng chia nhỏ tài liệu rồi gửi lại từng phần.")
        return pc

    for pat in INJECTION_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE | re.UNICODE)
        if m:
            snippet = m.group(0).strip()[:80]
            pc.flags.append({"code": "PROMPT_INJECTION",
                             "message": f"Phát hiện đoạn giống câu lệnh chèn trong tài liệu: “{snippet}”. "
                                        f"Đã coi là dữ liệu và bỏ qua."})
            break
    # vô hiệu hóa thẻ đóng giả để không thoát khỏi khối <document>
    text = re.sub(r"</?\s*(document|user_instruction|precheck_flags)\s*>", "[thẻ bị vô hiệu hóa]",
                  text, flags=re.IGNORECASE)
    pc.clean_text = text
    return pc


def build_user_message(instruction: str, document: str, flags=None) -> str:
    parts = ["<user_instruction>", (instruction or "").strip(), "</user_instruction>"]
    if flags:
        parts += ["<precheck_flags>", json.dumps(flags, ensure_ascii=False), "</precheck_flags>"]
    parts += ["<document>", document, "</document>"]
    return "\n".join(parts)
