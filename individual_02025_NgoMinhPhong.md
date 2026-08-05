# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | -------- |
| Họ và tên       | Ngô Minh Phong |
| MSSV            | 2A202602025 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Fullstack AI Agent Developer / Team Lead |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Data & Utils | `utils/data_loader.py`, `utils/evidence.py` | CSV files | DataStore objects, Evidence extraction | Hoàn thành |
| Extractor Agents | `payment_agent.py`, `order_seller_agent.py`, `delivery_agent.py` | Dữ liệu Orders, Items, Payments | Phân tích thanh toán, trạng thái giao hàng, lỗi | Hoàn thành |
| Decision Agents | `policy_agent.py`, `verifier_agent.py`, `coordinator.py` | JSON facts từ Extractor Agents | Quyết định bồi thường, Validation lỗi, Orchestration | Hoàn thành |
| Pipeline & Scripts | `main.py`, `scripts/zip_output.py`, test scripts | Toàn bộ components | File `output.zip` hoàn chỉnh | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Xây dựng toàn bộ hệ thống | Toàn bộ dự án | Tự thiết kế và lập trình toàn bộ pipeline End-to-End từ load data đến xuất JSON. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Khởi tạo Data Store và trích xuất dữ liệu | `data_loader.py`, `order_seller_agent.py` | Load thành công 99k+ orders và 3k+ sellers | Chạy test loader không bị lỗi bộ nhớ |
| Viết rules phân xử thanh toán và giao hàng | `payment_agent.py`, `delivery_agent.py` | Tính đúng tiền split payment và lỗi trễ hạn | Test khớp với test cases |
| Đưa ra quyết định Policy và Orchestrate | `policy_agent.py`, `coordinator.py`, `main.py` | Pipeline tự động hóa hoàn toàn 50 edge cases | Nộp hệ thống đạt 95.7515% |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Tạo ra toàn bộ source code của hệ thống và file kết quả cuối cùng `output.zip` chứa 50 JSON files tương ứng với 50 Edge Cases, đạt điểm xuất sắc 95.7515% trên hệ thống Grader.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Bài toán yêu cầu xây dựng một hệ thống Multi-Agent hoàn chỉnh để đánh giá tự động các đơn hàng thương mại điện tử bị lỗi (Giao muộn, Bị hủy, Thanh toán sai). Vấn đề là phải thiết kế kiến trúc sao cho các Agents phối hợp nhịp nhàng, truyền dữ liệu chính xác cho nhau và đưa ra quyết định bồi thường đúng chuẩn định dạng yêu cầu.

### Cách triển khai
Tôi thiết kế kiến trúc theo hướng **Deterministic Multi-Agent (A2A)**:
1. **Extractor Agents**: Đọc dữ liệu từ `DataStore`. `order_seller_agent` gom nhóm thông tin, `payment_agent` đối soát số tiền (dùng Epsilon 0.10 để bù trừ sai số), `delivery_agent` tính toán thời gian trễ đến từng giây.
2. **Decision Agent (`policy_agent`)**: Nhận facts dưới dạng cấu trúc dữ liệu và chạy qua cây quyết định khắt khe (Priority rules) để ra phán quyết cuối.
3. **Orchestrator (`coordinator.py` & `main.py`)**: Điều phối luồng gọi tuần tự giữa các agent và xử lý ghi file JSON. Tôi quyết định giữ logic thuần Python (Deterministic) thay vì dùng LLM để tối đa hóa điểm số và tốc độ chạy (chỉ 26s cho 50 cases).

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | Dữ liệu thô từ các file CSV (`orders`, `items`, `payments`, `sellers`) |
| Output                  | JSON Schema chứa Assessment, Entities, Root Cause và Evidence |
| Module phụ thuộc        | Các hàm utils và agent do chính tay tôi viết |
| Module sử dụng output   | `main.py` dùng `Coordinator` để xuất dữ liệu ra thư mục `output/` |
| Điều kiện lỗi cần xử lý | Missing timestamps, sai số dấu phẩy động trong payment, format JSON chặt chẽ. |

### Cách xác minh

```bash
python main.py
python scripts/zip_output.py
```

- **Kết quả mong đợi:** Toàn bộ pipeline chạy mượt mà, ghi đủ 50 file JSON, pass qua Verifier Agent.
- **Kết quả thực tế:** Tạo thành công `output.zip`, điểm chấm trên hệ thống đạt 95.7515%.
- **Artifact/log:** `output.zip` và `logging/trace.jsonl`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Quyết định có nên tích hợp LLM (GPT-4o) vào phần phân tích Policy hay dùng hàm Python thuần (Deterministic rules).
- **Các phương án đã cân nhắc:** 1) Gọi OpenAI API (GPT-4o) để đưa ra phán quyết. 2) Dùng if-else logic thuần khắt khe.
- **Phương án đã chọn:** Dùng if-else logic thuần (Deterministic) cho toàn bộ pipeline.
- **Lý do:** Khi thử nghiệm LLM, mặc dù logic có vẻ "thông minh" hơn nhưng hay trả về sai format chuỗi chuẩn (`full_refund` thay vì `issue_full_refund`), khiến điểm bị tụt nghiêm trọng xuống 60%. Hệ thống Grader chấm dựa trên keyword tĩnh và thời gian chính xác tới từng giây, nên việc dùng Deterministic đảm bảo tính ổn định tuyệt đối (Reproducibility 100%), điểm số cao nhất (95.75%) và tiết kiệm chi phí/thời gian chạy.
- **Bằng chứng quyết định phù hợp:** Phiên bản Deterministic chạy trong 26 giây với điểm 95.7515%, tốt hơn so với pipeline 2.5 phút của LLM.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Điểm số bị tụt ~2.73% khi cố gắng "thông minh hóa" logic giao hàng (cho phép giao trễ trong cùng một ngày).
- **Lệnh hoặc bước tái hiện:** Thay đổi `carrier_date.date() > shipping_limit_date.date()` trong `delivery_agent.py`.
- **Nguyên nhân gốc:** Hệ thống chấm điểm yêu cầu strict comparison đến từng giây. Việc bỏ qua giờ/phút khiến một số đơn hàng trễ vài tiếng bị quy sai thành đúng hạn.
- **Cách xử lý:** Tôi đã review lại trace log của từng case, test thử và nhanh chóng Revert lại logic so sánh timestamp nguyên gốc (`>`).
- **Cách xác minh sau khi sửa:** Chạy lại toàn bộ `main.py` và lấy lại thành công mốc 95.7515%.
- **Điều học được:** Khi làm việc với Data Engineering và Grader, phải tôn trọng tuyệt đối Spec kỹ thuật và không được tự ý "làm tròn" hay đưa common sense vào mã nguồn nếu không có trong tài liệu.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
*(Lưu ý: Template chứa câu hỏi của bài lab khác, xin phép trả lời theo concept chung)*: Dữ liệu crawl qua Crossref API, được tiền xử lý (text extraction, chunking), đưa qua Embedding model để tạo vector, rồi lưu vào Vector Database.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
Evaluation set chứa cặp câu hỏi-đáp. Ground-truth IDs giúp đối chiếu xem các chunks được retrieve từ VectorDB có trùng với ID của tài liệu gốc hay không (đo lường Recall/Precision).
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
Quality check phát hiện dữ liệu rỗng/lỗi định dạng khi crawl. Freshness monitoring theo dõi độ mới của dữ liệu để trigger update khi có nội dung mới.
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
Để đảm bảo fair comparison (tính công bằng) khi so sánh hiệu suất trước và sau quá trình cải tiến hệ thống.
5. Repair được xem là thành công dựa trên artifact và metric nào?
Khi các metric (Accuracy, Retrieval Rate) trên repaired pipeline vượt baseline/corrupted, minh chứng rõ ràng qua artifact logs.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Ngô Minh Phong
**Ngày xác nhận:** 2026-08-05
