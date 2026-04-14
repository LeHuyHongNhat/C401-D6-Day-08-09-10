# Scorecard — Variant Hybrid
**Thời gian chạy:** 2026-04-13 18:02 

## RAGAS Metrics
| Metric | Score | Target | Status |
|---|---|---|---|---|
| Faithfulness | 0.20 | > 0.90 | ❌ |
| Relevance | 0.20 | > 0.85 | ❌ |
| Context Recall | 0.10 | > 0.80 | ❌ |
| Completeness | 0.20 | > 0.80 | ❌ |
| Abstain Accuracy | 0.00 | = 1.00 | ❌ |

## Per-question Results
| ID | Category | Expected | Got | Pass? |
|---|---|---|---|---|
| q01 | SLA | Ticket P1 có SLA phản hồi ban đầu 15 phút và thời ... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q02 | Refund | Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 n... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q03 | Access Control | Level 3 (Elevated Access) cần phê duyệt từ Line Ma... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q04 | Refund | Không. Theo chính sách hoàn tiền, sản phẩm thuộc d... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q05 | IT Helpdesk | Tài khoản bị khóa sau 5 lần đăng nhập sai liên tiế... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q06 | SLA | Ticket P1 tự động escalate lên Senior Engineer nếu... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q07 | Access Control | Tài liệu 'Approval Matrix for System Access' hiện ... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q08 | HR Policy | Nhân viên sau probation period có thể làm remote t... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q09 | Insufficient Context | Không tìm thấy thông tin về ERR-403-AUTH trong tài... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
| q10 | Refund | Tài liệu chính sách hoàn tiền không đề cập đến quy... | ERROR: [Errno 2] No such file or directory: './dat... | ❌ |
