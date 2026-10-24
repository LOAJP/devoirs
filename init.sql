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

-- 座位表
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

-- 初始数据
INSERT INTO admin (username, password) VALUES ('admin', '123456');
INSERT INTO student (username, password, student_name) VALUES
('stu01', '123456', '张三'),
('stu02', '123456', '李四');
INSERT INTO study_room (room_name, remark) VALUES
('图书馆自习室A', '一楼安静区'),
('教学楼自习室B', '三楼');
INSERT INTO seat (room_id, seat_no) VALUES
(1, 'A01'), (1, 'A02'), (1, 'A03'),
(2, 'B01'), (2, 'B02');
