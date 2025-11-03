from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "clave_secreta_123"

# Conexión a MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="******",
    database="ahorrosdb"
)
cursor = db.cursor(dictionary=True)

# RUTA REGISTRO 
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        telefono = request.form['telefono']
        dni = request.form['dni']

        cursor.execute(
            "INSERT INTO usuarios (nombre, correo, contrasena, telefono, dni) VALUES (%s,%s,%s,%s,%s)",
            (nombre, correo, contrasena, telefono, dni)
        )
        db.commit()
        flash("Usuario registrado correctamente ", "success")
        return redirect('/login')

    return render_template('registro.html')


#  RUTA LOGIN 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contrasena']

        cursor.execute(
            "SELECT id, nombre FROM usuarios WHERE correo=%s AND contrasena=%s",
            (correo, contrasena)
        )
        user = cursor.fetchone()

        if user:
            session['usuario_id'] = user['id']
            session['nombre'] = user['nombre']
            return redirect('/')
        else:
            flash(" Correo o contraseña incorrectos", "danger")

    return render_template('login.html')


#  RUTA INDEX 
@app.route('/')
def index():
    usuario = session.get('nombre')
    return render_template('index.html', usuario=usuario)


#  RUTA LISTAR GASTOS 
@app.route('/gastos')
def listar_gastos():
    if 'usuario_id' not in session:
        return redirect('/login')

    cursor.execute(
        "SELECT * FROM gastos WHERE usuario_id=%s ORDER BY fecha DESC",
        (session['usuario_id'],)
    )
    gastos = cursor.fetchall()

    cursor.execute(
        "SELECT SUM(monto) AS total FROM gastos WHERE usuario_id=%s",
        (session['usuario_id'],)
    )
    total = cursor.fetchone()['total'] or 0

    return render_template('gastos_lista.html', gastos=gastos, total=total)


#  RUTA REGISTRAR GASTO 
@app.route('/gastos/registrar', methods=['GET', 'POST'])
def registrar_gasto():
    if 'usuario_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        monto = request.form['monto']
        categoria = request.form['categoria']
        descripcion = request.form['descripcion']

        cursor.execute(
            "INSERT INTO gastos (usuario_id, monto, categoria, descripcion) VALUES (%s,%s,%s,%s)",
            (session['usuario_id'], monto, categoria, descripcion)
        )
        db.commit()
        flash("💰 Gasto registrado correctamente", "success")
        return redirect('/gastos')

    return render_template('registrar_gasto.html')


#  RUTA EDITAR GASTO 
@app.route('/gastos/editar/<int:id>', methods=['GET', 'POST'])
def editar_gasto(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        monto = request.form['monto']
        categoria = request.form['categoria']
        descripcion = request.form['descripcion']

        cursor.execute("""
            UPDATE gastos SET monto=%s, categoria=%s, descripcion=%s
            WHERE id=%s AND usuario_id=%s
        """, (monto, categoria, descripcion, id, session['usuario_id']))
        db.commit()
        flash("✏️ Gasto actualizado correctamente", "info")
        return redirect('/gastos')

    cursor.execute(
        "SELECT * FROM gastos WHERE id=%s AND usuario_id=%s",
        (id, session['usuario_id'])
    )
    gasto = cursor.fetchone()
    return render_template('gastos_editar.html', gasto=gasto)


#  RUTA ELIMINAR GASTO 
@app.route('/gastos/eliminar/<int:id>')
def eliminar_gasto(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    cursor.execute(
        "DELETE FROM gastos WHERE id=%s AND usuario_id=%s",
        (id, session['usuario_id'])
    )
    db.commit()
    flash("🗑️ Gasto eliminado correctamente", "danger")
    return redirect('/gastos')


#  RUTA LOGOUT 
@app.route('/logout')
def logout():
    session.clear()
    flash("Cerraste sesión correctamente 👋", "info")
    return redirect('/login')
#  RUTA ESTADÍSTICAS 
@app.route('/estadisticas')
def estadisticas():
    if 'usuario_id' not in session:
        return redirect('/login')

    #  Gastos por categoría
    cursor.execute("""
        SELECT categoria, SUM(monto) AS total
        FROM gastos
        WHERE usuario_id=%s
        GROUP BY categoria
    """, (session['usuario_id'],))
    gastos_categoria = cursor.fetchall()

    #  Gastos por mes 
    cursor.execute("""
        SELECT DATE_FORMAT(fecha, '%Y-%m') AS mes, SUM(monto) AS total
        FROM gastos
        WHERE usuario_id=%s
        GROUP BY mes
        ORDER BY mes
    """, (session['usuario_id'],))
    gastos_mes = cursor.fetchall()

    return render_template(
        'estadisticas.html',
        usuario=session.get('nombre'),
        gastos_categoria=gastos_categoria,
        gastos_mes=gastos_mes
    )



# MAIN 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
