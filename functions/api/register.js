import { jsonResponse, errorResponse } from './_shared.js';

export async function onRequestPost(context) {
    try {
        const { request, env } = context;
        const body = await request.json();

        const prefix = (body.prefix || "").trim();
        const firstname = (body.firstname || "").trim();
        const lastname = (body.lastname || "").trim();
        const level = (body.level || "").trim();
        const room = parseInt(body.room);
        const number = parseInt(body.number);
        const club_id = parseInt(body.club_id);

        if (!prefix) return errorResponse("กรุณาเลือกคำนำหน้า");
        if (!firstname) return errorResponse("กรุณากรอกชื่อ");
        if (!lastname) return errorResponse("กรุณากรอกนามสกุล");
        if (!level) return errorResponse("กรุณาเลือกระดับชั้น");
        if (!room) return errorResponse("กรุณาเลือกห้อง");
        if (!number) return errorResponse("กรุณากรอกเลขที่");
        if (!club_id) return errorResponse("กรุณาเลือกชุมนุม");

        if (!["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6"].includes(level)) {
            return errorResponse("ระดับชั้นไม่ถูกต้อง");
        }
        if (![1, 2, 3, 4].includes(room)) {
            return errorResponse("ห้องเรียนต้องเป็น 1, 2, 3 หรือ 4 เท่านั้น");
        }
        if (number <= 0) return errorResponse("เลขที่ต้องมากกว่า 0");

        // Check if registration is active
        const { results: settings } = await env.DB.prepare("SELECT key, value FROM settings").all();
        const settingsMap = {};
        settings.forEach(s => settingsMap[s.key] = s.value);

        if (settingsMap.reg_status === 'closed') {
            return errorResponse("ขณะนี้ระบบปิดรับลงทะเบียนชั่วคราวโดยผู้ดูแลระบบ");
        }
        
        const now = new Date();
        // Adjust for Thai timezone roughly for checking (UTC+7)
        const tzOffset = 7 * 60 * 60000;
        const localNow = new Date(now.getTime() + tzOffset);
        const nowStr = localNow.toISOString().slice(0, 16);

        if (settingsMap.reg_start && nowStr < settingsMap.reg_start) {
            return errorResponse("ระบบยังไม่เปิดให้ลงทะเบียน");
        }
        if (settingsMap.reg_end && nowStr > settingsMap.reg_end) {
            return errorResponse("ระบบได้ปิดรับลงทะเบียนเนื่องจากหมดกำหนดเวลาแล้ว");
        }

        // Fetch club info for the receipt and grade limit
        const clubInfo = await env.DB.prepare("SELECT name, capacity, grade_limit FROM clubs WHERE id = ?").bind(club_id).first();
        if (!clubInfo) return errorResponse("ไม่พบรหัสชุมนุมที่ระบุ");

        if (clubInfo.grade_limit === 'high_school' && !["ม.4", "ม.5", "ม.6"].includes(level)) {
            return errorResponse(`ชุมนุม '${clubInfo.name}' รับสมัครเฉพาะนักเรียนระดับชั้นมัธยมศึกษาตอนปลาย (ม.4 - ม.6)`);
        }

        // Generate current timestamp string for DB
        const timestamp = localNow.toISOString().replace('T', ' ').slice(0, 19);

        // Atomic Insert to prevent race conditions
        try {
            const insertResult = await env.DB.prepare(`
                INSERT INTO students (prefix, firstname, lastname, level, room, number, club_id, registered_at)
                SELECT ?, ?, ?, ?, ?, ?, ?, ?
                WHERE (SELECT COUNT(*) FROM students WHERE club_id = ?) < ?
            `).bind(prefix, firstname, lastname, level, room, number, club_id, timestamp, club_id, clubInfo.capacity).run();

            if (insertResult.meta.changes === 0) {
                return errorResponse("ขออภัย ชุมนุมนี้เต็มแล้ว กรุณาเลือกชุมนุมอื่น");
            }
        } catch (dbErr) {
            const errMsg = dbErr.message || "";
            if (errMsg.includes("UNIQUE constraint failed: students.firstname, students.lastname")) {
                return errorResponse("ชื่อและนามสกุลนี้ได้ทำการลงทะเบียนไปแล้ว");
            }
            if (errMsg.includes("UNIQUE constraint failed: students.level, students.room, students.number")) {
                return errorResponse("ระดับชั้น ห้อง และเลขที่นี้ได้ทำการลงทะเบียนไปแล้ว");
            }
            return errorResponse("เกิดข้อผิดพลาดในการลงทะเบียน: " + errMsg);
        }

        return jsonResponse({
            success: true,
            student: {
                prefix,
                firstname,
                lastname,
                level,
                room,
                number,
                club_name: clubInfo.name,
                registered_at: timestamp
            }
        });

    } catch (e) {
        return errorResponse("ข้อมูล JSON ไม่ถูกต้อง หรือเกิดข้อผิดพลาดเซิร์ฟเวอร์", 500);
    }
}
