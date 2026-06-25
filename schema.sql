DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS clubs;
DROP TABLE IF EXISTS settings;

CREATE TABLE clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    teacher TEXT NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 30,
    grade_limit TEXT NOT NULL DEFAULT 'none'
);

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prefix TEXT NOT NULL,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    level TEXT NOT NULL,
    room INTEGER NOT NULL,
    number INTEGER NOT NULL,
    club_id INTEGER NOT NULL,
    registered_at TEXT NOT NULL,
    FOREIGN KEY(club_id) REFERENCES clubs(id),
    UNIQUE(firstname, lastname),
    UNIQUE(level, room, number)
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Insert default settings
INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', 'admin121314');
INSERT OR IGNORE INTO settings (key, value) VALUES ('reg_start', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('reg_end', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('reg_status', 'open');

-- Insert default clubs
INSERT INTO clubs (name, teacher, capacity, grade_limit) VALUES 
('Crossword', 'ครูนวพล', 30, 'none'),
('วอลเลย์บอล', 'ครูวันเฉลิม', 30, 'none'),
('Nw band', 'ครูวิศิษฐ์', 30, 'none'),
('SUDOKU', 'ครูจุฑามาศ', 30, 'none'),
('คณิตศิลป์', 'ครูวรรณลักษณ์', 30, 'none'),
('นาฏศิลป์สร้างสรรค์', 'ครูนาฏศิลป์', 30, 'none'),
('เรียนจีนง่ายๆไปกับครูต้อง', 'ครูปวีณา', 30, 'none'),
('Time Machine', 'ครูพิจิตรา', 30, 'none'),
('ช่างคิด ช่างทำ', 'ครูจิรพัฒน์', 30, 'none'),
('การ์ตูนล้อ', 'ครูธัญญรัศม์', 30, 'none'),
('Esports', 'ครูปริศา', 30, 'none'),
('บริษัทสร้างการดี', 'ครูสุธิดา', 30, 'none'),
('สภานักเรียน รับเฉพาะม.ปลาย', 'ครูบัณฑิต', 30, 'high_school'),
('บริษัทสร้างการดี', 'ครูณัฐนิช', 30, 'none'),
('สภานักเรียนรับเฉพาะม.ปลาย', 'ครูเพ็ญจันทร์', 30, 'high_school'),
('โมเดลกระดาษ', 'ครูวิไลลักษณ์', 30, 'none'),
('A-MATH', 'ครูศรัญญา', 30, 'none'),
('นาวงคาเฟ่', 'ครูอารยา', 30, 'none');
