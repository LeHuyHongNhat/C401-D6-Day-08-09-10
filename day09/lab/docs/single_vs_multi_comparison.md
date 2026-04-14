# Comparison: Single Agent (Day 08) vs Multi-Agent (Day 09)

Hệ thống Day 09 không chỉ là một đợt nâng cấp về code mà là một bước nhảy vọt về kiến trúc Orchestration. Dưới đây là phân tích chi tiết sự khác biệt dựa trên dữ liệu thực tế.

---

## 1. Bảng số liệu so sánh Hiệu năng

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Thay đổi |
|--------|----------------------|----------------------|----------|
| **Faithfulness** | 0.84 | **0.88** | +0.04 |
| **Relevance** | 0.84 | 0.82 | -0.02 |
| **Context Recall** | **0.96** | 0.92 | -0.04 |
| **Completeness** | 0.64 | **0.82** | +0.18 |
| **Avg Latency** | **~3,200ms** | 3,851ms | +651ms |
| **Routing Visibility**| Không có | **Rất cao (Reason log)** | N/A |

---

## 2. Phân tích sự Đánh đổi Architectural (Trade-offs)

### 2.1 Tính Minh bạch vs. Hiệu năng (Transparency vs. Performance)
Đây là sự đánh đổi lớn nhất của kiến trúc Supervisor-Worker.
- **Latency**: Day 09 có độ trễ tăng nhẹ (~20%) so với Day 08. Mặc dù phải qua nhiều node trung gian (`Supervisor -> Worker -> Synthesis`), việc tối ưu hóa architecture đã giúp giữ mức response time ở ngưỡng 4s, hoàn toàn chấp nhận được cho UX.
- **Transparency**: Đổi lại, nhóm có khả năng **gỡ lỗi tức thì (Zero-guess debugging)**. 
    - Ở Day 08, khi AI trả lời sai, nhóm mất trung bình 15-20 phút để truy vết xem lỗi ở bước Embedding hay Generation.
    - Ở Day 09, nhờ `route_reason` và `worker_io_log`, nhóm chỉ mất **2 phút** để xác định Supervisor đã route đúng hay chưa và Worker đã nhận đủ context chưa.

### 2.2 Độ đầy đủ và Chính xác (Completeness & Robustness)
- **Quan sát**: Chỉ số `Completeness` tăng mạnh (+0.11).
- **Lý do**: Synthesis Worker ở Day 09 nhận được Context đã được **Policy Tool** tiền xử lý. Việc bóc tách các "Exception Flags" (e.g. `flash_sale_exception`) giúp LLM Synthesis không bị sót các điều kiện loại trừ, điều mà mô hình Monolith Day 08 thường xuyên bị "quên" do context window bị nhiễu.

---

## 3. Khả năng mở rộng (Extensibility & MCP)

| Kịch bản thay đổi | Day 08 (Single Agent) | Day 09 (Multi-Agent) |
|-------------------|-----------------------|-----------------------|
| **Thêm 1 tool/API mới** | Phải sửa toàn bộ Prompt lớn, dễ gây side-effect. | Chỉ cần thêm MCP tool và cập nhật route rule trong Supervisor. |
| **Update logic xử lý** | Sửa code core pipeline, rủi ro hồi quy (regression) cao. | Sửa riêng trong Worker cụ thể (VD: chỉ sửa logic trong `policy_tool.py`). |
| **A/B Testing** | Phải clone toàn bộ pipeline cực kỳ cồng kềnh. | Có thể chạy A/B test riêng lẻ từng Worker (VD: test 2 loại Retrieval worker khác nhau). |

---

## 4. Khi nào nên dùng Multi-Agent? (Kết luận từ Nhóm)

Dựa trên kết quả thực tế, nhóm AI in Action rút ra kết luận:
1. **Dùng Multi-Agent khi**: 
    - Hệ thống cần thực thi các logic nghiệp vụ rẽ nhánh phức tạp (như Access Control kết hợp SLA).
    - Yêu cầu tính audit và giải trình cao cho từng bước suy luận.
    - Cần tích hợp nhiều công cụ bên thứ 3 qua chuẩn MCP.
2. **Dùng Single Agent khi**: 
    - Ưu tiên trải nghiệm người dùng thực thời (Real-time).
    - Các domain kiến thức hẹp, ít rẽ nhánh và không yêu cầu tool-calling phức tạp.

## 5. Tổng kết

Day 09 là minh chứng cho việc **kiến trúc tốt có thể bù đắp cho sự gia tăng độ trễ**. Mặc dù hệ thống chạy chậm hơn, nhưng sự gia tăng về độ tin cậy và khả năng bảo trì khiến mô hình Multi-Agent trở thành lựa chọn tối ưu cho các hệ thống Enterprise support trong tương lai.
