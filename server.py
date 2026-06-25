import os
import sys
import json
import sqlite3
import secrets
import urllib.parse
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import csv

DB_FILE = os.path.join(os.path.dirname(__file__), "database.db")
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")

# Global in-memory admin session token (resets if server restarts, which is safe and standard)
session_token = secrets.token_hex(16)

def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Detect if database has the old schema (has fullname instead of firstname/lastname)
    # If so, we can drop the students table or delete the db file to recreate it cleanly since we are in dev.
    if os.path.exists(DB_FILE):
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT fullname FROM students LIMIT 1")
            # If this succeeds, it's the old schema. We close connection and delete database to recreate.
            conn.close()
            print("Detected old database schema. Recreating database...")
            try:
                os.remove(DB_FILE)
            except Exception as e:
                print("Could not delete old db file automatically. Dropping students table instead.")
                conn2 = get_db()
                conn2.execute("DROP TABLE IF EXISTS students")
                conn2.commit()
                conn2.close()
        except sqlite3.OperationalError:
            # Table doesn't exist or doesn't have fullname (which means it's already new or clean)
            conn.close()

    conn = get_db()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        teacher TEXT NOT NULL,
        capacity INTEGER NOT NULL DEFAULT 30,
        grade_limit TEXT NOT NULL DEFAULT 'none' -- 'none' or 'high_school'
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
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
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    
    # Insert default settings
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', 'admin121314')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reg_start', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reg_end', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reg_status', 'open')") # 'open' or 'closed'
    
    # Check if clubs are empty, if so, insert the 18 clubs
    cursor.execute("SELECT COUNT(*) FROM clubs")
    if cursor.fetchone()[0] == 0:
        default_clubs = [
            ("Crossword", "ครูนวพล", 30, "none"),
            ("วอลเลย์บอล", "ครูวันเฉลิม", 30, "none"),
            ("Nw band", "ครูวิศิษฐ์", 30, "none"),
            ("SUDOKU", "ครูจุฑามาศ", 30, "none"),
            ("คณิตศิลป์", "ครูวรรณลักษณ์", 30, "none"),
            ("นาฏศิลป์สร้างสรรค์", "ครูนาฏศิลป์", 30, "none"),
            ("เรียนจีนง่ายๆไปกับครูต้อง", "ครูปวีณา", 30, "none"),
            ("Time Machine", "ครูพิจิตรา", 30, "none"),
            ("ช่างคิด ช่างทำ", "ครูจิรพัฒน์", 30, "none"),
            ("การ์ตูนล้อ", "ครูธัญญรัศม์", 30, "none"),
            ("Esports", "ครูปริศา", 30, "none"),
            ("บริษัทสร้างการดี", "ครูสุธิดา", 30, "none"),
            ("สภานักเรียน รับเฉพาะม.ปลาย", "ครูบัณฑิต", 30, "high_school"),
            ("บริษัทสร้างการดี", "ครูณัฐนิช", 30, "none"),
            ("สภานักเรียนรับเฉพาะม.ปลาย", "ครูเพ็ญจันทร์", 30, "high_school"),
            ("โมเดลกระดาษ", "ครูวิไลลักษณ์", 30, "none"),
            ("A-MATH", "ครูศรัญญา", 30, "none"),
            ("นาวงคาเฟ่", "ครูอารยา", 30, "none")
        ]
        cursor.executemany(
            "INSERT INTO clubs (name, teacher, capacity, grade_limit) VALUES (?, ?, ?, ?)",
            default_clubs
        )
    
    conn.commit()
    conn.close()

class ClubRequestHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Clean logging output
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format%args))

    def check_admin_auth(self):
        auth_header = self.headers.get("X-Admin-Token")
        return auth_header == session_token

    def serve_static(self, file_path):
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File not found")
            return
        
        # Determine content type
        _, ext = os.path.splitext(file_path)
        content_type = "text/plain; charset=utf-8"
        if ext == ".html":
            content_type = "text/html; charset=utf-8"
        elif ext == ".css":
            content_type = "text/css; charset=utf-8"
        elif ext == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif ext == ".json":
            content_type = "application/json; charset=utf-8"
        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".ico"]:
            content_type = f"image/{ext[1:]}"
            
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

    def send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_error(self, message, status_code=400):
        self.send_json({"error": message}, status_code)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Route API endpoints
        if path == "/api/clubs":
            self.handle_get_clubs()
        elif path == "/api/admin/settings":
            self.handle_get_settings()
        elif path == "/api/admin/registrations":
            self.handle_get_registrations()
        elif path == "/api/admin/export":
            self.handle_export_csv()
        elif path == "/api/admin/check-auth":
            if self.check_admin_auth():
                self.send_json({"authenticated": True})
            else:
                self.send_json({"authenticated": False}, 401)
        # Route Web Pages and Static Files
        else:
            # Map clean URLs to HTML files
            if path == "/":
                file_path = os.path.join(PUBLIC_DIR, "index.html")
            elif path == "/admin":
                file_path = os.path.join(PUBLIC_DIR, "admin.html")
            elif path == "/success":
                file_path = os.path.join(PUBLIC_DIR, "success.html")
            else:
                # Serve from public directory
                rel_path = path.lstrip("/")
                file_path = os.path.join(PUBLIC_DIR, rel_path)
            
            self.serve_static(file_path)

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Read content length
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
        
        try:
            body = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self.send_error("ข้อมูล JSON ไม่ถูกต้อง")
            return

        if path == "/api/register":
            self.handle_register(body)
        elif path == "/api/admin/login":
            self.handle_admin_login(body)
        elif path == "/api/admin/settings":
            self.handle_save_settings(body)
        elif path == "/api/admin/clubs":
            self.handle_create_club(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
        try:
            body = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self.send_error("ข้อมูล JSON ไม่ถูกต้อง")
            return

        if path.startswith("/api/admin/clubs/"):
            club_id = path.split("/")[-1]
            self.handle_update_club(club_id, body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path.startswith("/api/admin/registrations/"):
            student_id = path.split("/")[-1]
            self.handle_delete_registration(student_id)
        elif path.startswith("/api/admin/clubs/"):
            club_id = path.split("/")[-1]
            self.handle_delete_club(club_id)
        else:
            self.send_response(404)
            self.end_headers()

    # --- API HANDLERS ---

    def handle_get_clubs(self):
        conn = get_db()
        cursor = conn.cursor()
        # Fetch clubs with registration counts
        cursor.execute("""
            SELECT c.id, c.name, c.teacher, c.capacity, c.grade_limit, 
                   COUNT(s.id) as registered 
            FROM clubs c 
            LEFT JOIN students s ON c.id = s.club_id 
            GROUP BY c.id
        """)
        clubs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        self.send_json(clubs)

    def handle_get_settings(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        settings = {row["key"]: row["value"] for row in cursor.fetchall()}
        conn.close()
        
        # Do not return actual admin password, just status & timing
        if "admin_password" in settings:
            del settings["admin_password"]
        self.send_json(settings)

    def check_registration_active(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        settings = {row["key"]: row["value"] for row in cursor.fetchall()}
        conn.close()

        # Check manual toggle
        if settings.get("reg_status", "open") == "closed":
            return False, "ขณะนี้ระบบปิดรับลงทะเบียนชั่วคราวโดยผู้ดูแลระบบ"

        # Check date/time bounds
        now_str = datetime.now().isoformat()[:16] # "YYYY-MM-DDTHH:MM"
        
        reg_start = settings.get("reg_start", "")
        reg_end = settings.get("reg_end", "")
        
        if reg_start and now_str < reg_start:
            # Format display time for Thai layout
            start_dt = datetime.fromisoformat(reg_start)
            return False, f"ระบบจะเริ่มเปิดให้ลงทะเบียนในวันที่ {start_dt.strftime('%d/%m/%Y')} เวลา {start_dt.strftime('%H:%M')} น."
            
        if reg_end and now_str > reg_end:
            return False, "ระบบได้ปิดรับลงทะเบียนเนื่องจากหมดกำหนดเวลาแล้ว"
            
        return True, ""

    def handle_register(self, body):
        # 1. Check if registration window is active
        is_active, message = self.check_registration_active()
        if not is_active:
            self.send_error(message)
            return

        # 2. Extract and sanitize inputs
        prefix = body.get("prefix", "").strip()
        firstname = body.get("firstname", "").strip()
        lastname = body.get("lastname", "").strip()
        level = body.get("level", "").strip()
        room = body.get("room")
        number = body.get("number")
        club_id = body.get("club_id")

        if not prefix:
            self.send_error("กรุณาเลือกคำนำหน้า")
            return
        if not firstname:
            self.send_error("กรุณากรอกชื่อ")
            return
        if not lastname:
            self.send_error("กรุณากรอกนามสกุล")
            return
        if not level:
            self.send_error("กรุณาเลือกระดับชั้น")
            return
        if not room:
            self.send_error("กรุณาเลือกห้อง")
            return
        if not number:
            self.send_error("กรุณากรอกเลขที่")
            return
        if not club_id:
            self.send_error("กรุณาเลือกชุมนุม")
            return

        try:
            room = int(room)
            number = int(number)
            club_id = int(club_id)
        except ValueError:
            self.send_error("ข้อมูลห้องและเลขที่ต้องเป็นตัวเลขเท่านั้น")
            return

        if level not in ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6"]:
            self.send_error("ระดับชั้นไม่ถูกต้อง")
            return

        if room not in [1, 2, 3, 4]:
            self.send_error("ห้องเรียนต้องเป็น 1, 2, 3 หรือ 4 เท่านั้น")
            return

        if number <= 0:
            self.send_error("เลขที่ต้องมากกว่า 0")
            return

        # 3. Process registration inside SQLite transaction to prevent race conditions
        conn = get_db()
        try:
            conn.execute("BEGIN IMMEDIATE TRANSACTION")
            cursor = conn.cursor()

            # Check duplicate student name
            cursor.execute("SELECT id FROM students WHERE firstname = ? AND lastname = ?", (firstname, lastname))
            if cursor.fetchone():
                conn.rollback()
                self.send_error("ชื่อและนามสกุลนี้ได้ทำการลงทะเบียนไปแล้ว")
                return

            # Check duplicate class room number
            cursor.execute("SELECT id FROM students WHERE level = ? AND room = ? AND number = ?", (level, room, number))
            if cursor.fetchone():
                conn.rollback()
                self.send_error("ระดับชั้น ห้อง และเลขที่นี้ได้ทำการลงทะเบียนไปแล้ว")
                return

            # Check club existence & details
            cursor.execute("SELECT id, name, capacity, grade_limit FROM clubs WHERE id = ?", (club_id,))
            club = cursor.fetchone()
            if not club:
                conn.rollback()
                self.send_error("ไม่พบรหัสชุมนุมที่ระบุ")
                return

            # Check grade limits (High school only)
            if club["grade_limit"] == "high_school" and level not in ["ม.4", "ม.5", "ม.6"]:
                conn.rollback()
                self.send_error(f"ชุมนุม '{club['name']}' รับสมัครเฉพาะนักเรียนระดับชั้นมัธยมศึกษาตอนปลาย (ม.4 - ม.6)")
                return

            # Check seat capacity
            cursor.execute("SELECT COUNT(*) FROM students WHERE club_id = ?", (club_id,))
            registered_count = cursor.fetchone()[0]
            if registered_count >= club["capacity"]:
                conn.rollback()
                self.send_error("ขออภัย ชุมนุมนี้เต็มแล้ว กรุณาเลือกชุมนุมอื่น")
                return

            # Insert registration record
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO students (prefix, firstname, lastname, level, room, number, club_id, registered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (prefix, firstname, lastname, level, room, number, club_id, now_str))

            conn.commit()
            
            # Send success response with receipt details
            self.send_json({
                "success": True,
                "student": {
                    "prefix": prefix,
                    "firstname": firstname,
                    "lastname": lastname,
                    "level": level,
                    "room": room,
                    "number": number,
                    "club_name": club["name"],
                    "registered_at": now_str
                }
            })
        except sqlite3.Error as e:
            conn.rollback()
            self.send_error(f"เกิดข้อผิดพลาดในการลงทะเบียน: {str(e)}")
        finally:
            conn.close()

    # --- ADMIN HANDLERS ---

    def handle_admin_login(self, body):
        password = body.get("password", "")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'admin_password'")
        admin_pass = cursor.fetchone()["value"]
        conn.close()

        if password == admin_pass:
            self.send_json({"token": session_token})
        else:
            self.send_error("รหัสผ่านไม่ถูกต้อง", 401)

    def handle_get_registrations(self):
        if not self.check_admin_auth():
            self.send_error("ไม่อนุญาตให้เข้าถึงระบบ", 401)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.prefix, s.firstname, s.lastname, s.level, s.room, s.number, s.registered_at,
                   c.name as club_name, c.teacher as club_teacher
            FROM students s
            JOIN clubs c ON s.club_id = c.id
            ORDER BY c.name, s.level, s.room, s.number
        """)
        students = [dict(row) for row in cursor.fetchall()]
        conn.close()
        self.send_json(students)

    def handle_delete_registration(self, student_id):
        if not self.check_admin_auth():
            self.send_error("ไม่อนุญาตให้เข้าถึงระบบ", 401)
            return

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
            conn.commit()
            self.send_json({"success": True})
        except sqlite3.Error as e:
            self.send_error(f"Cannot delete student: {str(e)}")
        finally:
            conn.close()

    def handle_save_settings(self, body):
        if not self.check_admin_auth():
            self.send_error("ไม่อนุญาตให้เข้าถึงระบบ", 401)
            return

        reg_start = body.get("reg_start", "")
        reg_end = body.get("reg_end", "")
        reg_status = body.get("reg_status", "open")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'reg_start'", (reg_start,))
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'reg_end'", (reg_end,))
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'reg_status'", (reg_status,))
        
        # Optional: update admin password if provided
        new_pass = body.get("admin_password", "")
        if new_pass:
            cursor.execute("UPDATE settings SET value = ? WHERE key = 'admin_password'", (new_pass,))
            
        conn.commit()
        conn.close()
        self.send_json({"success": True})

    def handle_create_club(self, body):
        if not self.check_admin_auth():
            self.send_error("ไม่อนุญาตให้เข้าถึงระบบ", 401)
            return

        name = body.get("name", "").strip()
        teacher = body.get("teacher", "").strip()
        capacity = body.get("capacity", 30)
        grade_limit = body.get("grade_limit", "none")

        if not (name and teacher):
            self.send_error("กรุณากรอกชื่อชุมนุมและชื่อครูผู้ดูแล")
            return

        try:
            capacity = int(capacity)
        except ValueError:
            self.send_error("จำนวนความจุต้องเป็นตัวเลข")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clubs (name, teacher, capacity, grade_limit)
            VALUES (?, ?, ?, ?)
        """, (name, teacher, capacity, grade_limit))
        conn.commit()
        conn.close()
        self.send_json({"success": True})

    def handle_update_club(self, club_id, body):
        if not self.check_admin_auth():
            self.send_error("ไม่อนุญาตให้เข้าถึงระบบ", 401)
            return

        name = body.get("name", "").strip()
        teacher = body.get("teacher", "").strip()
        capacity = body.get("capacity")
        grade_limit = body.get("grade_limit", "none")

        if not (name and teacher):
            self.send_error("กรุณากรอกชื่อชุมนุมและชื่อครูผู้ดูแล")
            return

        try:
            capacity = int(capacity)
        except ValueError:
            self.send_error("จำนวนความจุต้องเป็นตัวเลข")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clubs 
            SET name = ?, teacher = ?, capacity = ?, grade_limit = ?
            WHERE id = ?
        """, (name, teacher, capacity, grade_limit, club_id))
        conn.commit()
        conn.close()
        self.send_json({"success": True})

    def handle_delete_club(self, club_id):
        if not self.check_admin_auth():
            self.send_error("ไม่อนุญาตให้เข้าถึงระบบ", 401)
            return

        conn = get_db()
        cursor = conn.cursor()
        
        # Verify if any student is registered in this club
        cursor.execute("SELECT COUNT(*) FROM students WHERE club_id = ?", (club_id,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            self.send_error("ไม่สามารถลบชุมนุมนี้ได้เนื่องจากมีนักเรียนสมัครเรียนอยู่ (กรุณาย้ายหรือลบนักเรียนในชุมนุมนี้ออกก่อน)")
            return

        cursor.execute("DELETE FROM clubs WHERE id = ?", (club_id,))
        conn.commit()
        conn.close()
        self.send_json({"success": True})

    def handle_export_csv(self):
        # We allow auth token via URL query string to make download links simple
        parsed_url = urllib.parse.urlparse(self.path)
        queries = urllib.parse.parse_qs(parsed_url.query)
        token = queries.get("token", [""])[0]

        if token != session_token:
            self.send_response(401)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Unauthorized access. Please login again.")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.prefix, s.firstname, s.lastname, s.level, s.room, s.number, s.registered_at,
                   c.name as club_name, c.teacher as club_teacher
            FROM students s
            JOIN clubs c ON s.club_id = c.id
            ORDER BY c.name, s.level, s.room, s.number
        """)
        students = cursor.fetchall()
        conn.close()

        # Send response headers for file download
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=club_registrations.csv")
        self.end_headers()

        # Write UTF-8 BOM so MS Excel opens Thai characters correctly
        self.wfile.write(b'\xef\xbb\xbf')

        # Generate CSV using Python's csv writer
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ลำดับที่", "คำนำหน้า", "ชื่อ", "นามสกุล", "ระดับชั้น", "ห้อง", "เลขที่", "ชุมนุมที่เลือก", "ครูผู้ดูแลชุมนุม", "เวลาที่สมัคร"])

        for idx, row in enumerate(students, 1):
            writer.writerow([
                idx,
                row["prefix"],
                row["firstname"],
                row["lastname"],
                row["level"],
                row["room"],
                row["number"],
                row["club_name"],
                row["club_teacher"],
                row["registered_at"]
            ])

        self.wfile.write(output.getvalue().encode("utf-8"))

def main():
    init_db()
    
    # Create public directory if not exists
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    
    port = 8000
    server_address = ("", port)
    
    # Using ThreadingHTTPServer to handle concurrency safely
    httpd = ThreadingHTTPServer(server_address, ClubRequestHandler)
    print(f"Server starting on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    main()
