import { jsonResponse, errorResponse, checkAuth } from '../../_shared.js';

export async function onRequestDelete(context) {
    const { request, env, params } = context;
    if (!(await checkAuth(request, env))) return errorResponse("ไม่อนุญาตให้เข้าถึงระบบ", 401);

    const studentId = params.id;
    if (!studentId) return errorResponse("ไม่ระบุรหัสนักเรียน", 400);

    try {
        await env.DB.prepare("DELETE FROM students WHERE id = ?").bind(studentId).run();
        return jsonResponse({ success: true });
    } catch (e) {
        return errorResponse("เกิดข้อผิดพลาดในการลบ: " + e.message, 500);
    }
}
