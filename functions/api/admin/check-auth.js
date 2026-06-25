import { jsonResponse, errorResponse, checkAuth } from '../_shared.js';

export async function onRequestGet(context) {
    const { request, env } = context;
    const isAuth = await checkAuth(request, env);
    if (isAuth) {
        return jsonResponse({ authenticated: true });
    } else {
        return errorResponse("ไม่อนุญาตให้เข้าถึงระบบ", 401);
    }
}
