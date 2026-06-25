import { jsonResponse, errorResponse, checkAuth } from '../../_shared.js';

export async function onRequestGet(context) {
    const { request, env } = context;
    if (!(await checkAuth(request, env))) return errorResponse("ไม่อนุญาตให้เข้าถึงระบบ", 401);

    const { results } = await env.DB.prepare(`
        SELECT s.id, s.prefix, s.firstname, s.lastname, s.level, s.room, s.number, s.registered_at,
               c.name as club_name, c.teacher as club_teacher
        FROM students s
        JOIN clubs c ON s.club_id = c.id
        ORDER BY c.name, s.level, s.room, s.number
    `).all();

    return jsonResponse(results || []);
}
