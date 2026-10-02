# Báo cáo Task 1 — Agent Arena, lịch README §3

Ngày: 2026-10-02. Phạm vi: làm quen, xây dựng năm middleware, kiểm chứng offline và chuẩn bị nộp `harness/`.

## Kết quả triển khai

- `critic`: giữ nguyên claim có bằng chứng; bỏ claim bịa; tách câu ghép tại ` và ` chỉ khi hai đoạn nguyên văn có nguồn quan sát khác nhau; abstain khi không đủ căn cứ.
- `citation_checker`: sửa nguồn bằng đối chiếu nguyên văn trong một dòng tài liệu đã quan sát; không viết lại claim.
- `injection_guard`: cách ly nhiều đoạn chèn lệnh, kể cả đoạn thiếu dấu đóng; loại canary khỏi answer.
- `budget_policy`: nhắc FINAL bằng sentinel và chặn công cụ khi chỉ còn lượt dành cho submit.
- `retry`: thử tối đa ba lần, nhận diện lỗi/suy giảm và tự giữ ngân sách submit; ghi bộ đếm vào context.
- Thêm sáu test tình huống trong `tests/test_student_layers.py`.

Không hard-code brief/doc_id, không dựa vào tags, không đổi prompt hay MAX_STEPS. Giữ nguyên chỉnh sửa README có sẵn của người dùng.

## Bằng chứng

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python scripts/run_practice.py --layers none --entry baseline --out runs/task01_baseline.json
python scripts/run_practice.py --out runs/task01_full.json
python -m pytest -q tests/test_student_layers.py tests/test_layers_stubs.py
python scripts/verify.py
```

- Baseline: **24.27/100**. Full stack: **81.7116/100**, tăng khoảng **57.44** điểm.
- Tất cả chín lượt full stack qua trace gate.
- Test layer và runnable-stack: **24 passed**.
- Kiểm chứng core sau phục hồi LF: **612 passed** (middleware, student layers, layer stubs, model, tools, scorer, synthesis, trace, corpus, briefs).
- `scripts/verify.py`: **21/21 đạt**.
- Leave-one-out: bỏ injection_guard **72.6430**; critic **69.7712**; citation_checker **52.6164**; budget_policy **74.9258**; retry **73.8521**. Từng layer đều đóng góp trên seed mặc định.
- Artefact chi tiết nằm trong `runs/task01_*.json` và log `runs/task01_*.txt` (được Git ignore).

## Giới hạn và vấn đề môi trường

- GUIDE.md và RUBRIC.md được README dẫn tới nhưng không có trong checkout.
- `python` hiện là Python 3.11.9; README đề nghị 3.12+, còn verifier chấp nhận 3.10+. Không cài thêm Python/dependency trong lần này.
- Checkout CRLF làm sai hash năm file arena đóng băng. Đã phục hồi đúng byte LF từ HEAD sau khi kiểm tra nội dung chỉ khác newline; hash đều khớp chuẩn và Git diff không có thay đổi mã arena. Không đưa arena vào commit.
- Full pytest trước khi phục hồi newline: **749 passed, 9 failed, 1 skipped, 8 errors** với UTF-8. Các lỗi có sẵn: hash newline; test kỳ vọng dấu `/` trên Windows; subprocess tự chọn encoding không hỗ trợ Unicode; PYTEST_CURRENT_TEST dài quá giới hạn biến môi trường Windows (32767 ký tự). Không sửa test hoặc arena để che lỗi.
- Hai brief pub-08/pub-09 vẫn có grounding 0: middleware không bổ sung chiến lược tìm kiếm sâu cho baseline. Điểm luyện tập không phải điểm vòng chấm chính thức.
- Pha 105–120 phút cần giảng viên chạy private briefs/model thật. Không có bằng chứng live-provider hay điểm chính thức trong báo cáo này.

## Nộp bài

Chỉ stage năm file `harness/layers/*.py` đã sửa, test mới và báo cáo này. README có thay đổi trước phiên làm việc, arena và runs được loại khỏi commit. Trạng thái commit/push được thông báo trực tiếp sau khi thực hiện và kiểm chứng remote.
