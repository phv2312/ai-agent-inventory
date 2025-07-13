1. Cho 2 câu bên dưới:
Câu 1:
{{ first_sentence }}
Câu 2:
{{ second_sentence }}

2. Hãy thực hiện các bước sau:
- Bỏ qua các ký tự không mang nghĩa như \n, ^, vv.
- Bỏ qua các khác biệt về nhấn nhá (ví dụ: có/không nháy kép, cách xuống dòng, chèn cảm thán).
- Chỉ tập trung vào ý nghĩa chính của câu – tức là mục đích truyền đạt của từng câu.
- So sánh ý nghĩa 2 câu và trả về kết quả theo hướng dẫn bên dưới:
a. is_same_meaning:
- Trả về True nếu 2 câu này có cùng một nội dung chính hoặc cùng mục đích truyền đạt, dù có khác về  : con số (số tiền, khoản tiền, nhiều/ ít, giàu/ nghèo, số bước) , thời gian (mốc thời gian ~ tháng/ ~ năm, khoản thời gian, tuổi tác, ngắn / dài, lâu/ mau/ nhanh/ lẹ )
- Trả về False nếu nội dung hoặc mục đích chính có khác biệt mục đích truyền đạt
c. reason:
- Trả về lý do THEO ĐỊNH DẠNG sau:
   - Nếu is_same_meaning = True, thì trả về:
<câu 1>: liệt kê các điểm khác biệt , chỉ khi nôi dung là:  con số (số tiền, khoản tiền, nhiều/ ít, giàu/ nghèo, số bước) , thời gian (mốc thời gian ~ tháng/ ~ năm, khoản thời gian, tuổi tác, ngắn / dài, lâu/ mau/ nhanh/ lẹ . Ngăn cách bằng dấu phẩy ",". Trường hợp liệt kê con số, thời gian, vv, tránh dùng từ "cụ thể", thay vào đó là để nội dung trong cặp dấu đơn ()
<câu 2>: liệt kê khác biệt tương ứng ở câu 1. Ngăn cách bằng dấu phẩy ","
Ví dụ:
reason:
<câu 1>: không nêu số tiền vay,  60 tháng
<câu 2>: số tiền vay (35 triệu), không nêu thời hạn vay
- Nếu is_same_meaning = False, thì trả về:
<câu 1>: có/ không đề cập gì so với câu 2, mọi khía cạnh (con số, thời gian, xưng hô, ý tứ) . Ngăn cách bằng dấu phẩy ",". Trường hợp liệt kê con số, thời gian, vv, tránh dùng từ "cụ thể", thay vào đó là để nội dung trong cặp dấu đơn ()
<câu 2>: có / không đề cập gì so với câu 1. Ngăn cách bằng dấu phẩy ","
- Ưu tiên rút gọn. Phân tách các điểm bằng dấu phẩy , thay vì viết thành câu dài. Không mô tả rườm rà.
