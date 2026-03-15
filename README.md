Task Management System - Backend API Test
Dự án này là hệ thống quản lý công việc (giống mini Jira / Trello) được xây dựng theo các yêu cầu bắt buộc của bài kiểm tra Backend. Hệ thống tập trung vào việc quản lý thực thể, tối ưu hiệu năng và xử lý sự kiện real-time.
Tech Stack (Yêu cầu bắt buộc)

Framework: Python FastAPI 


Cơ sở dữ liệu: MongoDB 


Caching & Pub/Sub: Redis 


Containerization: Docker & Docker Compose 

Kiến trúc Hệ thống (System Architecture)
Hệ thống tuân thủ mô hình: Client => FastAPI => MongoDB & Redis.

1. Database Design (MongoDB)
Thiết kế các Collections bao gồm: users, tasks, projects, comments, activity_logs.


Chiến lược Reference: Sử dụng ObjectId để liên kết Task với Project và User (Assignee).


Chiến lược Embedded: Nhúng comments trực tiếp vào tài liệu tasks để tối ưu tốc độ truy xuất.


Indexing: Thiết lập Unique Index cho email người dùng và Compound Index cho bộ lọc trạng thái công việc.

2. Tính năng nâng cao

Redis Caching: Áp dụng cho endpoint chi tiết Task với TTL 60s để giảm tải cho database.


Aggregation: Sử dụng MongoDB Aggregation Pipeline để thống kê số lượng task theo trạng thái.


Event System (Pub/Sub): Khi Task được tạo/cập nhật, một event sẽ được publish qua Redis để ghi lại Activity Log.

API Endpoints chính

User Management: 


POST /users: Tạo người dùng mới.


GET /users/{id}: Lấy thông tin chi tiết.


Task Management: 


POST /tasks: Tạo task kèm gán người nhận việc.


GET /tasks: Danh sách task (Hỗ trợ Pagination, Filtering).


GET /tasks/stats: Thống kê trạng thái công việc.


Activity Log: 


GET /logs: Xem lịch sử thay đổi hệ thống.
