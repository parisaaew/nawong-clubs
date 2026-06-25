import { jsonResponse, errorResponse, generateToken } from '../_shared.js';

export async function onRequestPost(context) {
    try {
        const { request, env } = context;
        const body = await request.json();
        
        const password = body.password || "";
        
        const result = await env.DB.prepare("SELECT value FROM settings WHERE key = 'admin_password'").first();
        if (!result) return errorResponse("การตั้งค่าผิดพลาด: ไม่พบรหัสผ่านในระบบ", 500);
        
        const adminPass = result.value;
        if (password === adminPass) {
            const token = await generateToken(adminPass);
            return jsonResponse({ token });
        } else {
            return errorResponse("รหัสผ่านไม่ถูกต้อง", 401);
        }
    } catch (e) {
        return errorResponse("ข้อมูลไม่ถูกต้อง", 400);
    }
}
