# 校园自习室座位预约管理系统
from datetime import datetime
from functools import wraps

import pymysql
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = 'study-room-demo-key'

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'study_room_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}


# ---------- 数据库工具 ----------
def get_conn():
    return pymysql.connect(**DB_CONFIG)


def query(sql, args=(), one=False):
    """查询，one=True 只返回第一行"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        conn.close()


def execute(sql, args=()):
    """增删改，自动提交、异常回滚"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            affected = cur.execute(sql, args)
        conn.commit()
        return affected
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------- 权限装饰器 ----------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('role'):
            flash('请先登录')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


def student_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'student':
            flash('请以学生身份登录')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('请以管理员身份登录')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper


# ---------- 座位状态辅助 ----------
def release_expired_seats():
    """惰性释放：有效预约全部结束的座位恢复空闲"""
    execute("""UPDATE seat s SET s.seat_status = 0
               WHERE s.seat_status = 1
                 AND EXISTS (SELECT 1 FROM reservation r0 WHERE r0.seat_id = s.seat_id)
                 AND NOT EXISTS (SELECT 1 FROM reservation r
                                 WHERE r.seat_id = s.seat_id AND r.res_status = 0 AND r.end_time > NOW())""")


def release_seat(seat_id):
    """取消预约后，若无其它有效预约则释放座位"""
    execute("""UPDATE seat s SET s.seat_status = 0
               WHERE s.seat_id = %s
                 AND NOT EXISTS (SELECT 1 FROM reservation r
                                 WHERE r.seat_id = %s AND r.res_status = 0 AND r.end_time > NOW())""",
            (seat_id, seat_id))


def parse_time(value):
    """解析 datetime-local 提交的时间"""
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except (TypeError, ValueError):
        return None


# ---------- 公共 ----------
@app.route('/')
def index():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_index'))
    if session.get('role') == 'student':
        return redirect(url_for('student_index'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role', 'student')
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('账号和密码不能为空')
            return redirect(url_for('login'))
        if role == 'admin':
            row = query('SELECT * FROM admin WHERE username=%s AND password=%s',
                        (username, password), one=True)
        else:
            row = query('SELECT * FROM student WHERE username=%s AND password=%s',
                        (username, password), one=True)
        if not row:
            flash('账号或密码错误')
            return redirect(url_for('login'))
        session.clear()
        session['role'] = role
        if role == 'admin':
            session['user_id'] = row['admin_id']
            session['username'] = row['username']
            return redirect(url_for('admin_index'))
        session['user_id'] = row['student_id']
        session['username'] = row['username']
        session['student_name'] = row['student_name']
        return redirect(url_for('student_index'))
    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    student_name = request.form.get('student_name', '').strip()
    if not username or not password or not student_name:
        flash('注册信息不能为空')
    elif len(username) > 50 or len(password) > 50 or len(student_name) > 50:
        flash('账号、密码、姓名均不能超过50个字符')
    elif query('SELECT student_id FROM student WHERE username=%s', (username,), one=True):
        flash('该账号已被注册')
    else:
        execute('INSERT INTO student (username, password, student_name) VALUES (%s, %s, %s)',
                (username, password, student_name))
        flash('注册成功，请登录')
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------- 学生端 ----------
@app.route('/student/index')
@student_required
def student_index():
    release_expired_seats()
    rooms = query('SELECT * FROM study_room ORDER BY room_id')
    rows = query('SELECT seat_id, room_id, seat_no FROM seat WHERE seat_status=0 ORDER BY seat_no')
    free_seats = {}
    for row in rows:
        free_seats.setdefault(row['room_id'], []).append(row)
    return render_template('student_index.html', rooms=rooms, free_seats=free_seats)


@app.route('/student/reserve', methods=['POST'])
@student_required
def student_reserve():
    seat_id = request.form.get('seat_id', type=int)
    start_time = parse_time(request.form.get('start_time', ''))
    end_time = parse_time(request.form.get('end_time', ''))
    if not seat_id or not start_time or not end_time:
        flash('请选择座位并填写完整的预约时间')
        return redirect(url_for('student_index'))
    if start_time < datetime.now():
        flash('开始时间不能早于当前时间')
    elif end_time <= start_time:
        flash('结束时间必须晚于开始时间')
    else:
        seat = query('SELECT * FROM seat WHERE seat_id=%s', (seat_id,), one=True)
        conflict = query("""SELECT res_id FROM reservation
                            WHERE seat_id=%s AND res_status=0 AND start_time < %s AND end_time > %s""",
                         (seat_id, end_time, start_time), one=True)
        if not seat:
            flash('座位不存在')
        elif seat['seat_status'] != 0:
            flash('该座位当前不可预约')
        elif conflict:
            flash('该座位在所选时间段已被预约')
        else:
            execute('INSERT INTO reservation (student_id, seat_id, start_time, end_time) VALUES (%s, %s, %s, %s)',
                    (session['user_id'], seat_id, start_time, end_time))
            execute('UPDATE seat SET seat_status=1 WHERE seat_id=%s', (seat_id,))
            flash('预约成功')
    return redirect(url_for('student_index'))


@app.route('/student/reservations')
@student_required
def student_reservations():
    release_expired_seats()
    rows = query("""SELECT r.res_id, r.start_time, r.end_time, r.create_time, r.res_status,
                           s.seat_no, sr.room_name
                    FROM reservation r
                    JOIN seat s ON r.seat_id = s.seat_id
                    JOIN study_room sr ON s.room_id = sr.room_id
                    WHERE r.student_id = %s
                    ORDER BY r.res_id DESC""", (session['user_id'],))
    return render_template('reserve_list.html', reservations=rows, now=datetime.now(), admin_view=False)


@app.route('/student/cancel/<int:res_id>', methods=['POST'])
@student_required
def student_cancel(res_id):
    row = query('SELECT * FROM reservation WHERE res_id=%s AND student_id=%s',
                (res_id, session['user_id']), one=True)
    if not row:
        flash('预约不存在')
    elif row['res_status'] != 0:
        flash('该预约已取消')
    elif row['start_time'] <= datetime.now():
        flash('预约已开始，不能取消')
    else:
        execute('UPDATE reservation SET res_status=1 WHERE res_id=%s', (res_id,))
        release_seat(row['seat_id'])
        flash('取消成功')
    return redirect(url_for('student_reservations'))


# ---------- 管理员端 ----------
@app.route('/admin/index')
@admin_required
def admin_index():
    students = query('SELECT student_id, username, student_name FROM student ORDER BY student_id')
    return render_template('admin_index.html', students=students)


@app.route('/admin/rooms')
@admin_required
def room_manage():
    rooms = query("""SELECT sr.room_id, sr.room_name, sr.remark,
                            (SELECT COUNT(*) FROM seat s WHERE s.room_id = sr.room_id) AS seat_count
                     FROM study_room sr ORDER BY sr.room_id""")
    return render_template('room_manage.html', rooms=rooms)


@app.route('/admin/room/add', methods=['POST'])
@admin_required
def room_add():
    room_name = request.form.get('room_name', '').strip()
    remark = request.form.get('remark', '').strip()
    if not room_name:
        flash('自习室名称不能为空')
    elif len(room_name) > 100 or len(remark) > 200:
        flash('名称不能超过100字符，备注不能超过200字符')
    else:
        execute('INSERT INTO study_room (room_name, remark) VALUES (%s, %s)', (room_name, remark or None))
        flash('新增自习室成功')
    return redirect(url_for('room_manage'))


@app.route('/admin/room/edit', methods=['POST'])
@admin_required
def room_edit():
    room_id = request.form.get('room_id', type=int)
    room_name = request.form.get('room_name', '').strip()
    remark = request.form.get('remark', '').strip()
    if not room_id or not room_name:
        flash('参数不完整')
    elif len(room_name) > 100 or len(remark) > 200:
        flash('名称或备注过长')
    else:
        execute('UPDATE study_room SET room_name=%s, remark=%s WHERE room_id=%s',
                (room_name, remark or None, room_id))
        flash('修改成功')
    return redirect(url_for('room_manage'))


@app.route('/admin/room/delete/<int:room_id>', methods=['POST'])
@admin_required
def room_delete(room_id):
    if query('SELECT seat_id FROM seat WHERE room_id=%s LIMIT 1', (room_id,), one=True):
        flash('该自习室下还有座位，请先删除座位')
    else:
        execute('DELETE FROM study_room WHERE room_id=%s', (room_id,))
        flash('删除成功')
    return redirect(url_for('room_manage'))


@app.route('/admin/seats')
@admin_required
def seat_manage():
    rooms = query('SELECT room_id, room_name FROM study_room ORDER BY room_id')
    room_id = request.args.get('room_id', type=int)
    if room_id is None and rooms:
        room_id = rooms[0]['room_id']
    seats = query('SELECT * FROM seat WHERE room_id=%s ORDER BY seat_id', (room_id,)) if room_id else []
    return render_template('seat_manage.html', rooms=rooms, seats=seats, room_id=room_id)


@app.route('/admin/seat/add', methods=['POST'])
@admin_required
def seat_add():
    room_id = request.form.get('room_id', type=int)
    seat_no = request.form.get('seat_no', '').strip()
    if not room_id or not seat_no:
        flash('请选择自习室并填写座位号')
    elif len(seat_no) > 30:
        flash('座位号不能超过30个字符')
    elif not query('SELECT room_id FROM study_room WHERE room_id=%s', (room_id,), one=True):
        flash('自习室不存在')
    elif query('SELECT seat_id FROM seat WHERE room_id=%s AND seat_no=%s', (room_id, seat_no), one=True):
        flash('该自习室已存在相同座位号')
    else:
        execute('INSERT INTO seat (room_id, seat_no) VALUES (%s, %s)', (room_id, seat_no))
        flash('新增座位成功')
    return redirect(url_for('seat_manage', room_id=room_id))


@app.route('/admin/seat/delete/<int:seat_id>', methods=['POST'])
@admin_required
def seat_delete(seat_id):
    seat = query('SELECT * FROM seat WHERE seat_id=%s', (seat_id,), one=True)
    if not seat:
        flash('座位不存在')
        return redirect(url_for('seat_manage'))
    if query('SELECT res_id FROM reservation WHERE seat_id=%s LIMIT 1', (seat_id,), one=True):
        flash('该座位已有预约记录，不能删除')
    else:
        execute('DELETE FROM seat WHERE seat_id=%s', (seat_id,))
        flash('删除成功')
    return redirect(url_for('seat_manage', room_id=seat['room_id']))


@app.route('/admin/seat/status', methods=['POST'])
@admin_required
def seat_status():
    seat_id = request.form.get('seat_id', type=int)
    status = request.form.get('seat_status', type=int)
    if not seat_id or status not in (0, 1):
        flash('参数错误')
    else:
        execute('UPDATE seat SET seat_status=%s WHERE seat_id=%s', (status, seat_id))
        flash('座位状态已更新')
    return redirect(url_for('seat_manage', room_id=request.form.get('room_id', type=int)))


@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    release_expired_seats()
    rows = query("""SELECT r.res_id, r.start_time, r.end_time, r.create_time, r.res_status,
                           st.student_name, st.username, s.seat_no, sr.room_name
                    FROM reservation r
                    JOIN student st ON r.student_id = st.student_id
                    JOIN seat s ON r.seat_id = s.seat_id
                    JOIN study_room sr ON s.room_id = sr.room_id
                    ORDER BY r.res_id DESC""")
    return render_template('reserve_list.html', reservations=rows, now=datetime.now(), admin_view=True)


@app.route('/admin/reservation/cancel/<int:res_id>', methods=['POST'])
@admin_required
def admin_cancel(res_id):
    row = query('SELECT * FROM reservation WHERE res_id=%s', (res_id,), one=True)
    if not row:
        flash('预约不存在')
    elif row['res_status'] != 0:
        flash('该预约已取消')
    else:
        execute('UPDATE reservation SET res_status=1 WHERE res_id=%s', (res_id,))
        release_seat(row['seat_id'])
        flash('已取消该预约')
    return redirect(url_for('admin_reservations'))


if __name__ == '__main__':
    app.run(debug=True)
