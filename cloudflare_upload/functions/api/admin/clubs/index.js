import { jsonResponse, errorResponse, checkAuth } from '../../_shared.js';

export async function onRequestPost(context) {
    const { request, env } = context;
    if (!(await checkAuth(request, env))) return errorResponse("ไม่อนุญาตให้เข้าถึงระบบ", 401);

    try {
        const body = await request.json();
        const name = (body.name || "").trim();
        const teacher = (body.teacher || "").trim();
        const capacity = parseInt(body.capacity) || 30;
        const grade_limit = body.grade_limit || "none";

        if (!name || !teacher) return errorResponse("กรุณากรอกชื่อชุมนุมและชื่อครูผู้ดูแล", 400);

        await env.DB.prepare(`
            INSERT INTO clubs (name, teacher, capacity, grade_limit)
            VALUES (?, ?, ?, ?)
        `).bind(name, teacher, capacity, grade_limit).run();

        return jsonResponse({ success: true });
    } catch (e) {
        return errorResponse("เกิดข้อผิดพลาด: " + e.message, 500);
    }
}
