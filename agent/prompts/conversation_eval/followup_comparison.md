1. Cho 2 câu bên dưới:
Câu 1
{{first_sentence}}
Câu 2:
{{second_sentence}}
2. Hãy thực hiện các bước sau:
- Bỏ qua các ký tự không mang nghĩa như \n, ^, vv.
- Bỏ qua các khác biệt về nhấn nhá (ví dụ: có/không nháy kép, cách xuống dòng, chèn cảm thán).
- Chỉ tập trung vào ý nghĩa chính của câu – tức là mục đích truyền đạt của từng câu.
- Trả về kết quả <câu 1> có giải đáp được thắc mắc của <câu 2> không và trả lời được bao nhiêu % ý cùa <câu 2> , theo quy tắc dưới đây:
a. confidence:  <câu 1> trả lời đúng ý <câu 2> được bao nhiêu %. Dựa vào tiêu chí : ý nghĩa, con số (tiền, khoản tiền) , thời gian (mốc thời gian, khoản thời gian, dài /ngắn, lâu/ mau/ nhanh chậm, tên , tuổi, vv)
b. is_concern_solved:
- Trả về True : nếu nội dung <câu 1> CÓ trả lời được ý của <câu 2>, hoặc <confidence> lớn hơn hoặc bằng 70%
- Trả về False nếu nội dung <câu 1> KHÔNG liên quan gì <câu 2>, hoặc <câu 1> chỉ trả lời được nhỏ hơn hoặc bằng 70% ý của <câu 2>
c. reason:
- Trả về lý do THEO ĐỊNH DẠNG sau:
   - Nếu is_concern_solved = True, thì trả về:
good_points: liệt kê các ý mà <câu 1> ĐÃ trả lời được ở <câu 2>. Ngăn cách bằng dấu phẩy ",". Trường hợp liệt kê con số, thời gian, vv, tránh dùng từ "cụ thể", thay vào đó là để nội dung trong cặp dấu đơn (). (ví dụ: (26%)).
notgood_points: Liệt kê các ý trong <câu 2> mà <câu 1> chưa trả lời được. Hoặc ghi "[]" nếu không còn ý nào chưa trả lời được. Lưu ý:  "notgood_points" tuyệt đối không được là con số, chữ số, số tiền, thời gian, kỳ hạn (bằng chữ hoặc số) . Nếu "notgood_points" là con số, chữ số, số tiền, thời gian, kỳ hạn (bằng chữ hoặc số)  thì liệt kê vào "good_points"
Ví dụ:
reason:
good_points: đã trả lời được khoản vay (99 triệu), đã trả lời được lãi suất (12%)
notgood_points: chưa trả lời được tên.
- Nếu is_concern_solved = False, thì trả về:
good_points: liệt kê các ý mà <câu 1> ĐÃ trả lời được ở <câu 2>. Ngăn cách bằng dấu phẩy ",". Trường hợp liệt kê con số, thời gian, vv, tránh dùng từ "cụ thể", thay vào đó là để nội dung trong cặp dấu đơn (). Hoặc ghi "không trả lời được user" nếu <câu 1> HOÀN TOÀN không có ý nào  trả lời được <câu 2> cả (tức <CS 2> =0%)
notgood_points: liệt kê các ý mà <câu 1> CHƯA trả lời được ở <câu 2>. Tức các ý làm cho <CS2> <70%
- Ưu tiên rút gọn. Phân tách các điểm bằng dấu phẩy , thay vì viết thành câu dài. Không mô tả rườm rà.
