# Design Template

## Problem

Hệ thống cần xử lý các câu hỏi nghiên cứu kỹ thuật phức tạp (ví dụ: so sánh kiến trúc Single-Agent vs Multi-Agent), yêu cầu:
1. Tìm kiếm và truy xuất các nguồn tài liệu tin cậy (offline corpus JSON / Tavily search).
2. Phân tích, so sánh các luận điểm, đánh giá mức độ tin cậy của bằng chứng và các trade-offs.
3. Tổng hợp thành một báo cáo nghiên cứu kỹ thuật hoàn chỉnh kèm trích dẫn (inline citations [source_id]).

## Why multi-agent?

- Single-agent baseline thường gộp toàn bộ quá trình tìm kiếm, phân tích và viết vào một prompt dài duy nhất, dẫn đến loãng ngữ cảnh (context dilution), khó kiểm soát quá trình kiểm chứng bằng chứng, và dễ xảy ra ảo giác (hallucination) do không có bước rà soát độc lập.
- Multi-agent phân tách trách nhiệm rõ ràng (Separation of Concerns): Researcher tập trung truy xuất và trích xuất sự thật; Analyst tập trung phân tích đánh giá đa chiều; Writer tập trung tổng hợp ngôn từ và trích dẫn chuẩn xác; Supervisor điều phối luồng và đảm bảo tiến độ.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| **Supervisor** | Điều phối luồng làm việc giữa các agent và kích hoạt điều kiện dừng | `ResearchState` | Cập nhật `route_history`, quyết định next node | Lặp vô hạn nếu thiếu stop condition |
| **Researcher** | Tìm kiếm dữ liệu từ kho tài liệu và trích xuất ghi chú nghiên cứu | `state.request.query`, `SearchClient` | `state.sources`, `state.research_notes` | Truy xuất nguồn rác hoặc thiếu nguồn liên quan |
| **Analyst** | Phân tích chuyên sâu, so sánh ưu/nhược điểm và đánh giá độ tin cậy nguồn | `state.research_notes`, `state.sources` | `state.analysis_notes` | Bỏ sót mâu thuẫn giữa các nguồn tài liệu |
| **Writer** | Viết báo cáo hoàn chỉnh dựa trên ghi chú và phân tích, gắn kèm citations | `state.research_notes`, `state.analysis_notes`, `state.sources` | `state.final_answer` | Bịa trích dẫn hoặc bỏ quên inline citation |
| **Critic (Optional)** | Kiểm chứng tính xác thực và độ phủ trích dẫn của câu trả lời cuối | `state.final_answer`, `state.sources` | Đánh giá factuality & citation audit | False consensus nếu lặp lại sai lệch ban đầu |

## Shared state

- `request`: Chứa câu hỏi gốc (`query`), số lượng nguồn tối đa (`max_sources`) và đối tượng độc giả (`audience`).
- `iteration`: Bộ đếm số bước lặp để phục vụ cơ chế guardrail `MAX_ITERATIONS`.
- `route_history`: Lưu vết các agent đã được gọi (ví dụ: `["researcher", "analyst", "writer", "done"]`).
- `sources`: Danh sách `SourceDocument` lưu thông tin tựa đề, snippet, URL và metadata provenance.
- `research_notes`: Ghi chú thô do Researcher tóm tắt từ các nguồn.
- `analysis_notes`: Báo cáo phân tích chuyên sâu của Analyst.
- `final_answer`: Báo cáo nghiên cứu hoàn chỉnh cuối cùng do Writer tổng hợp.
- `agent_results`: Danh sách log chi tiết của từng lượt agent chạy (kèm token count, cost, latency).
- `trace`: Lịch sử các span/sự kiện phục vụ observability.

## Routing policy

Workflow được xây dựng bằng LangGraph theo sơ đồ StateGraph:
1. `START` -> `supervisor`
2. `supervisor` kiểm tra state:
   - Nếu `not state.sources or not state.research_notes` -> chuyển sang `researcher`
   - Nếu `not state.analysis_notes` -> chuyển sang `analyst`
   - Nếu `not state.final_answer` -> chuyển sang `writer`
   - Nếu đã có đủ hoặc vượt quá `max_iterations` -> chuyển sang `END` (`done`)
3. Mỗi worker (`researcher`, `analyst`, `writer`) sau khi hoàn thành nhiệm vụ đều quay trở lại `supervisor` để điều phối bước kế tiếp.

## Guardrails

- **Max iterations**: Giới hạn tối đa số lượt điều phối (mặc định: 6) để ngắt vòng lặp vô hạn.
- **Timeout**: Timeout mạng và API gọi LLM/Search (mặc định: 60s).
- **Retry / Fallback**: Tự động thử lại với retry logic, fallback sang offline local corpus nếu không kết nối được Tavily API.
- **Validation**: Kiểm tra schema Pydantic chặt chẽ cho toàn bộ input, output và shared state.

## Benchmark plan

- **Queries**: Kiểm thử với bộ câu hỏi so sánh kiến trúc hệ thống multi-agent vs single-agent.
- **Metrics**:
  - Wall-clock latency (giây)
  - Estimated token cost (USD)
  - Quality score (thang 0-10)
  - Citation coverage (% nguồn được trích dẫn hợp lệ)
  - Failure rate (% lỗi thực thi)
- **Outcome**: Đã tạo báo cáo so sánh chi tiết tại `reports/benchmark_report.md`.
