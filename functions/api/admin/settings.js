import { jsonResponse, errorResponse, checkAuth } from '../_shared.js';

export async function onRequestGet(context) {
    const { env } = context;
    const { results } = await env.DB.prepare("SELECT key, value FROM settings").all();
    
    const settings = {};
    results.forEach(row => {
        if (row.key !== 'admin_password') {
            settings[row.key] = row.value;
        }
    });
    
    return jsonResponse(settings);
}

export async function onRequestPost(context) {
    const { request, env } = context;
    if (!(await checkAuth(request, env))) return errorResponse("ไม่อนุญาตให้เข้าถึงระบบ", 401);

    try {
        const body = await request.json();
        const reg_status = body.reg_status || "open";
        const reg_start = body.reg_start || "";
        const reg_end = body.reg_end || "";
        const new_pass = body.admin_password || "";

        // D1 Batch statement
        const stmts = [
            env.DB.prepare("UPDATE settings SET value = ? WHERE key = 'reg_status'").bind(reg_status),
            env.DB.prepare("UPDATE settings SET value = ? WHERE key = 'reg_start'").bind(reg_start),
            env.DB.prepare("UPDATE settings SET value = ? WHERE key = 'reg_end'").bind(reg_end),
        ];

        if (new_pass) {
            stmts.push(env.DB.prepare("UPDATE settings SET value = ? WHERE key = 'admin_password'").bind(new_pass));
        }

        await env.DB.batch(stmts);

        return jsonResponse({ success: true });
    } catch (e) {
        return errorResponse("เกิดข้อผิดพลาดในการบันทึก", 500);
    }
}
