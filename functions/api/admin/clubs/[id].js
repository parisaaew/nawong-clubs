import { jsonResponse, errorResponse, checkAuth } from '../../_shared.js';

export async function onRequestPut(context) {
    const { request, env, params } = context;
    if (!(await checkAuth(request, env))) return errorResponse("ไม่อนุญาตให้เข้าถึงระบบ", 401);

    const clubId = params.id;
    if (!clubId) return errorResponse("ไม่ระบุรหัสชุมนุม", 400);

    try {
        const body = await request.json();
        const name = (body.name || "").trim();
        const teacher = (body.teacher || "").trim();
        const capacity = parseInt(body.capacity) || 30;
        const grade_limit = body.grade_limit || "none";

        if (!name || !teacher) return errorResponse("กรุณากรอกชื่อชุมนุมและชื่อครูผู้ดูแล", 400);

        await env.DB.prepare(`
            UPDATE clubs 
            SET name = ?, teacher = ?, capacity = ?, grade_limit = ?
            WHERE id = ?
        `).bind(name, teacher, capacity, grade_limit, clubId).run();

        return jsonResponse({ success: true });
    } catch (e) {
        return errorResponse("เกิดข้อผิดพลาด: " + e.message, 500);
    }
}

export async function onRequestDelete(context) {
    const { request, env, params } = context;
    if (!(await checkAuth(request, env))) return errorResponse("ไม่อนุญาตให้เข้าถึงระบบ", 401);

    const clubId = params.id;
    if (!clubId) return errorResponse("ไม่ระบุรหัสชุมนุม", 400);

    try {
        // Verify if any student is registered in this club
        const { count } = await env.DB.prepare("SELECT COUNT(*) as count FROM students WHERE club_id = ?").bind(clubId).first();
        if (count > 0) {
            return errorResponse("ไม่สามารถลบชุมนุมนี้ได้เนื่องจากมีนักเรียนสมัครเรียนอยู่", 400);
        }

        await env.DB.prepare("DELETE FROM clubs WHERE id = ?").bind(clubId).run();
        return jsonResponse({ success: true });
    } catch (e) {
        return errorResponse("เกิดข้อผิดพลาด: " + e.message, 500);
    }
}
