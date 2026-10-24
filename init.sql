-- 校园自习室座位预约管理系统 建表脚本
DROP DATABASE IF EXISTS study_room_db;
CREATE DATABASE study_room_db DEFAULT CHARACTER SET utf8mb4;
USE study_room_db;

-- 学生表
CREATE TABLE student (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(50) NOT NULL,
    student_name VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 管理员表
CREATE TABLE admin (
    admin_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 自习室表
CREATE TABLE study_room (
    room_id INT PRIMARY KEY AUTO_INCREMENT,
    room_name VARCHAR(100) NOT NULL,
    remark VARCHAR(200) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 座位表（seat_status：0空闲 1已预约 2使用中 3故障）
CREATE TABLE seat (
    seat_id INT PRIMARY KEY AUTO_INCREMENT,
    room_id INT NOT NULL,
    seat_no VARCHAR(30) NOT NULL,
    seat_status TINYINT NOT NULL DEFAULT 0,
    CONSTRAINT fk_seat_room FOREIGN KEY (room_id) REFERENCES study_room (room_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 预约表
CREATE TABLE reservation (
    res_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    seat_id INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    res_status TINYINT NOT NULL DEFAULT 0,
    CONSTRAINT fk_res_student FOREIGN KEY (student_id) REFERENCES student (student_id) ON DELETE RESTRICT,
    CONSTRAINT fk_res_seat FOREIGN KEY (seat_id) REFERENCES seat (seat_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 初始账号
INSERT INTO admin (username, password) VALUES ('admin', '123456');
INSERT INTO student (username, password, student_name) VALUES
('stu01', '123456', '张三'),
('stu02', '123456', '李四');

-- 两间自习室
INSERT INTO study_room (room_name, remark) VALUES
('图书馆自习室A', '一楼安静区'),
('教学楼自习室B', '三楼');

-- 每间 30 个座位（6 列 × 5 排，第 2、4 列后为过道）
INSERT INTO seat (room_id, seat_no) VALUES
(1, 'A01'), (1, 'A02'), (1, 'A03'), (1, 'A04'), (1, 'A05'), (1, 'A06'),
(1, 'A07'), (1, 'A08'), (1, 'A09'), (1, 'A10'), (1, 'A11'), (1, 'A12'),
(1, 'A13'), (1, 'A14'), (1, 'A15'), (1, 'A16'), (1, 'A17'), (1, 'A18'),
(1, 'A19'), (1, 'A20'), (1, 'A21'), (1, 'A22'), (1, 'A23'), (1, 'A24'),
(1, 'A25'), (1, 'A26'), (1, 'A27'), (1, 'A28'), (1, 'A29'), (1, 'A30'),
(2, 'B01'), (2, 'B02'), (2, 'B03'), (2, 'B04'), (2, 'B05'), (2, 'B06'),
(2, 'B07'), (2, 'B08'), (2, 'B09'), (2, 'B10'), (2, 'B11'), (2, 'B12'),
(2, 'B13'), (2, 'B14'), (2, 'B15'), (2, 'B16'), (2, 'B17'), (2, 'B18'),
(2, 'B19'), (2, 'B20'), (2, 'B21'), (2, 'B22'), (2, 'B23'), (2, 'B24'),
(2, 'B25'), (2, 'B26'), (2, 'B27'), (2, 'B28'), (2, 'B29'), (2, 'B30');

-- 故障座位示例
UPDATE seat SET seat_status = 3 WHERE room_id = 1 AND seat_no IN ('A05', 'A06');

-- 演示：李四已预约明天 09:00-11:00 的 A01
INSERT INTO reservation (student_id, seat_id, start_time, end_time, res_status)
VALUES (2, 1, TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00:00'),
        TIMESTAMP(DATE_ADD(CURDATE(), INTERVAL 1 DAY), '11:00:00'), 0);
UPDATE seat SET seat_status = 1 WHERE seat_id = 1;
