from flask import Flask, request, render_template, redirect, url_for
import mysql.connector

app = Flask(__name__)

# MySQL config
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'RPRathod@24',
    'database': 'hostel_allocation'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)


# 🏠 Home page - list students
@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Student")
    students = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()
    return render_template('students.html', students=students, columns=columns)


# ➕ Add student
@app.route('/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        department = request.form['department']
        year = request.form['year']
        preferred_room_type = request.form['preferred_room_type']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Student (name, age, gender, department, year, preferred_room_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, age, gender, department, year, preferred_room_type))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('home'))

    return render_template('add_student.html')


# ✏️ Edit student
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        department = request.form['department']
        year = request.form['year']
        preferred_room_type = request.form['preferred_room_type']

        cursor.execute("""
            UPDATE Student 
            SET name=%s, age=%s, gender=%s, department=%s, year=%s, preferred_room_type=%s
            WHERE student_id=%s
        """, (name, age, gender, department, year, preferred_room_type, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('home'))

    cursor.execute("SELECT * FROM Student WHERE student_id = %s", (id,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('edit_student.html', student=student)


# Delete student
@app.route('/delete/<int:id>')
def delete_student(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Student WHERE student_id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('home'))

@app.route('/rooms')
def show_rooms():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Room")
    rooms = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()
    return render_template('rooms.html', rooms=rooms, columns=columns)

@app.route('/allocate', methods=['GET', 'POST'])
def allocate_room_manual():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']
        room_id = request.form['room_id']
        cursor.execute("""
            INSERT INTO allocation (student_id, room_id, allocation_date)
            VALUES (%s, %s, CURDATE())
        """, (student_id, room_id))
        conn.commit()
        conn.close()
        return redirect('/allocate')

    # 🧑‍🎓 Students not yet allocated (show name + preference)
    cursor.execute("""
        SELECT s.student_id, s.name, s.preferred_room_type
        FROM student s
        WHERE s.student_id NOT IN (SELECT student_id FROM allocation)
    """)
    students = cursor.fetchall()

    # 🏠 Available rooms
    cursor.execute("""
        SELECT r.room_id, r.room_code, r.room_type
        FROM room r
        WHERE r.room_id NOT IN (SELECT room_id FROM allocation)
    """)
    rooms = cursor.fetchall()

    # 🧾 Current allocations
    cursor.execute("""
        SELECT a.allocation_id, s.name AS student_name, s.preferred_room_type,
               r.room_code, r.room_type, a.allocation_date
        FROM allocation a
        JOIN student s ON a.student_id = s.student_id
        JOIN room r ON a.room_id = r.room_id
    """)
    allocations = cursor.fetchall()

    conn.close()
    return render_template('allocate.html', students=students, rooms=rooms, allocations=allocations)


@app.route('/auto_allocate', methods=['GET', 'POST'])
def allocate_room_smart():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']

        # Get student's preferred type
        cursor.execute("SELECT preferred_room_type FROM student WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            conn.close()
            return "<p>Error: Student not found.</p>"

        preferred_type = student['preferred_room_type']

        # Find available room with matching type
        cursor.execute("""
            SELECT r.room_id, r.room_code, r.capacity, COUNT(a.room_id) AS allocated
            FROM room r
            LEFT JOIN allocation a ON r.room_id = a.room_id
            WHERE r.room_type = %s AND r.room_type IS NOT NULL
            GROUP BY r.room_id, r.room_code, r.capacity
            HAVING allocated < r.capacity
            ORDER BY r.room_id ASC
            LIMIT 1
        """, (preferred_type,))
        room = cursor.fetchone()

        if not room:
            conn.close()
            return f"<p>No available rooms found for preference: {preferred_type}</p>"

        cursor.execute("""
            INSERT INTO allocation (student_id, room_id, allocation_date)
            VALUES (%s, %s, CURDATE())
        """, (student_id, room['room_id']))
        conn.commit()
        conn.close()
        return redirect('/auto_allocate')

    # Students not yet allocated
    cursor.execute("""
        SELECT s.student_id, s.name, s.preferred_room_type
        FROM student s
        WHERE s.student_id NOT IN (SELECT student_id FROM allocation)
    """)
    students = cursor.fetchall()

    # Current allocations
    cursor.execute("""
        SELECT a.allocation_id, s.name AS student_name, s.preferred_room_type,
               r.room_code, r.room_type, a.allocation_date
        FROM allocation a
        JOIN student s ON a.student_id = s.student_id
        JOIN room r ON a.room_id = r.room_id
    """)
    allocations = cursor.fetchall()

    conn.close()
    return render_template('allocate_auto.html', students=students, allocations=allocations)
    
@app.route('/')
def dashboard():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # Hostel details (can later come from DB)
    warden_name = "Mr. Rajdeep Rathod"
    hostel_name = "TechVille Boys Hostel"
    hostel_address = "TechVille Campus, Sector 21, Pune, Maharashtra, 411001"

    # Total students
    cursor.execute("SELECT COUNT(*) AS total_students FROM student")
    total_students = cursor.fetchone()['total_students']

    # Allocated students
    cursor.execute("SELECT COUNT(*) AS allocated_students FROM allocation")
    allocated_students = cursor.fetchone()['allocated_students']

    # Total rooms
    cursor.execute("SELECT COUNT(*) AS total_rooms FROM room")
    total_rooms = cursor.fetchone()['total_rooms']

    # Available rooms (capacity check)
    cursor.execute("""
        SELECT COUNT(*) AS available_rooms
        FROM room r
        LEFT JOIN allocation a ON r.room_id = a.room_id
        GROUP BY r.room_id
        HAVING COUNT(a.room_id) < r.capacity
    """)
    available_rooms = cursor.rowcount

    conn.close()

    return render_template(
        'dashboard.html',
        warden_name=warden_name,
        hostel_name=hostel_name,
        hostel_address=hostel_address,
        total_students=total_students,
        allocated_students=allocated_students,
        total_rooms=total_rooms,
        available_rooms=available_rooms
    )

if __name__ == '__main__':
    app.run(debug=True)