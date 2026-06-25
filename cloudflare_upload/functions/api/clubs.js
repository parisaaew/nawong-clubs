import { jsonResponse, errorResponse } from './_shared.js';

export async function onRequestGet(context) {
    try {
        const { env } = context;
        const { results } = await env.DB.prepare(`
            SELECT c.id, c.name, c.teacher, c.capacity, c.grade_limit, 
                   COUNT(s.id) as registered 
            FROM clubs c 
            LEFT JOIN students s ON c.id = s.club_id 
            GROUP BY c.id
        `).all();
        
        return jsonResponse(results || []);
    } catch (e) {
        return errorResponse(e.message, 500);
    }
}
