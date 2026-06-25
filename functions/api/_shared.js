export async function checkAuth(request, env) {
    const token = request.headers.get("X-Admin-Token");
    if (!token) return false;
    
    // Fetch password from DB
    const stmt = env.DB.prepare("SELECT value FROM settings WHERE key = 'admin_password'");
    const result = await stmt.first();
    if (!result || !result.value) return false;
    
    const adminPass = result.value;
    
    // Generate simple token by hashing the password
    const encoder = new TextEncoder();
    const keyData = encoder.encode(adminPass + "SECRET_SALT_2026");
    const hashBuffer = await crypto.subtle.digest('SHA-256', keyData);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const expectedToken = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    
    return token === expectedToken;
}

export async function generateToken(adminPass) {
    const encoder = new TextEncoder();
    const keyData = encoder.encode(adminPass + "SECRET_SALT_2026");
    const hashBuffer = await crypto.subtle.digest('SHA-256', keyData);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { 'Content-Type': 'application/json; charset=utf-8' }
    });
}

export function errorResponse(msg, status = 400) {
    return jsonResponse({ error: msg }, status);
}
