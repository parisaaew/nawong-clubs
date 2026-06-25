import { checkAuth } from '../_shared.js';

export async function onRequestGet(context) {
    const { request, env } = context;
    
    // Auth via token in query string since it's a file download link
    const url = new URL(request.url);
    const token = url.searchParams.get('token');
    
    // Mock a request with X-Admin-Token header to use our checkAuth function
    const mockRequest = new Request(request, {
        headers: new Headers({ 'X-Admin-Token': token || '' })
    });

    if (!(await checkAuth(mockRequest, env))) {
        return new Response("ไม่อนุญาตให้เข้าถึงระบบ", { status: 401 });
    }

    const { results } = await env.DB.prepare(`
        SELECT s.id, s.prefix, s.firstname, s.lastname, s.level, s.room, s.number, s.registered_at,
               c.name as club_name, c.teacher as club_teacher
        FROM students s
        JOIN clubs c ON s.club_id = c.id
        ORDER BY c.name, s.level, s.room, s.number
    `).all();

    let csvContent = '\uFEFF'; // UTF-8 BOM
    csvContent += "ลำดับที่,คำนำหน้า,ชื่อ,นามสกุล,ระดับชั้น,ห้อง,เลขที่,ชุมนุมที่เลือก,ครูผู้ดูแลชุมนุม,เวลาที่สมัคร\n";

    if (results) {
        results.forEach((row, idx) => {
            csvContent += `${idx + 1},${row.prefix},${row.firstname},${row.lastname},${row.level},${row.room},${row.number},${row.club_name},${row.club_teacher},${row.registered_at}\n`;
        });
    }

    return new Response(csvContent, {
        headers: {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename=club_registrations.csv'
        }
    });
}
