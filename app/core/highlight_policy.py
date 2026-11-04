"""Export eligibility: AI scores rank candidates; they never require approval."""
def selection_allows_export(result):
    if not isinstance(result, dict):
        return True
    audit = result.get("selection")
    if not isinstance(audit, dict):
        return result.get("auto_export_allowed") is not False
    # 01/11/2026 (anh Hùng: "phân tích kiểu gì cũng phải ra Part, không báo
    # vàng, không trả về video"): có Part là XUẤT. Phân tích cụt vì hết lượt AI
    # không còn tới được đây — m1 tự đợi key hồi rồi phân tích lại phần thiếu
    # (`DoiLuotAI`, cổng 103) trước khi chốt kết quả.
    return bool(result.get("count", 0))


def selection_note(result):
    if not isinstance(result, dict):
        return ""
    audit = result.get("selection") or {}
    if isinstance(audit, dict) and audit.get("quality_review_required") and selection_allows_export(result):
        return (f"Đã tạo {result.get('count', 0)} Part. Điểm chỉ để xếp hạng; "
                "không cần duyệt vì điểm thấp. Xem trạng thái xuất ở từng Part.")
    return str(result.get("selection_note") or "")
