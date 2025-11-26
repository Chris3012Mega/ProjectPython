from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from datetime import datetime

# POO y FUNCIONAL
from modelos import Usuario, Gasto, AnalizadorGastos
from funciones import promedio_gastos


app = Flask(__name__)
app.secret_key = "clave_secreta_123"


# ===================== CONEXIÓN ======================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Iece5728",
    database="ahorrosdb"
)
cursor = db.cursor(dictionary=True)


# ===================== REGISTRO ======================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        datos = (
            request.form['nombre'],
            request.form['correo'],
            request.form['contrasena'],
            request.form['telefono'],
            request.form['dni']
        )
        cursor.execute("""
            INSERT INTO usuarios(nombre,correo,contrasena,telefono,dni)
            VALUES(%s,%s,%s,%s,%s)
        """, datos)
        db.commit()
        flash("Usuario creado correctamente", "success")
        return redirect('/login')

    return render_template('registro.html')


# ===================== LOGIN ======================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cursor.execute("""
            SELECT id,nombre,correo FROM usuarios
            WHERE correo=%s AND contrasena=%s
        """, (request.form['correo'], request.form['contrasena']))
        fila = cursor.fetchone()

        if fila:
            usuario = Usuario(fila['id'], fila['nombre'], fila['correo'])
            session['usuario_id'] = usuario.id
            session['nombre'] = usuario.nombre
            return redirect('/')
        else:
            flash("Datos incorrectos", "danger")

    return render_template('login.html')


# ===================== INDEX ======================
@app.route('/')
def index():
    return render_template('index.html', usuario=session.get('nombre'))


# ===================== GASTOS ======================
@app.route('/gastos')
def listar_gastos():
    if 'usuario_id' not in session: return redirect('/login')

    cursor.execute("SELECT * FROM gastos WHERE usuario_id=%s ORDER BY fecha DESC",
                   (session['usuario_id'],))
    gastos = cursor.fetchall()

    cursor.execute("SELECT SUM(monto) AS total FROM gastos WHERE usuario_id=%s",
                   (session['usuario_id'],))
    total = cursor.fetchone()['total'] or 0

    return render_template("gastos_lista.html", gastos=gastos, total=total)


@app.route('/gastos/registrar', methods=['GET','POST'])
def registrar_gasto():
    if 'usuario_id' not in session: return redirect('/login')

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO gastos(usuario_id,monto,categoria,descripcion)
            VALUES(%s,%s,%s,%s)
        """, (session['usuario_id'],
              request.form['monto'],
              request.form['categoria'],
              request.form['descripcion']))
        db.commit()
        flash("Gasto registrado", "success")
        return redirect('/gastos')

    return render_template("registrar_gasto.html")


@app.route('/gastos/eliminar/<int:id>')
def eliminar_gasto(id):
    if 'usuario_id' not in session: return redirect('/login')

    cursor.execute("DELETE FROM gastos WHERE id=%s AND usuario_id=%s",
                   (id, session['usuario_id']))
    db.commit()
    flash("Gasto eliminado", "danger")
    return redirect('/gastos')


# ===================== META DE AHORRO ======================
@app.route('/meta', methods=['GET','POST'])
def meta():
    if 'usuario_id' not in session: return redirect('/login')

    mes = datetime.now().strftime('%Y-%m')

    if request.method == 'POST':
        monto = request.form['monto_meta']

        cursor.execute("""
            SELECT id FROM metas_ahorro
            WHERE usuario_id=%s AND mes=%s
        """, (session['usuario_id'], mes))
        existe = cursor.fetchone()

        if existe:
            cursor.execute("""
                UPDATE metas_ahorro
                SET monto_meta=%s
                WHERE usuario_id=%s AND mes=%s
            """, (monto, session['usuario_id'], mes))
        else:
            cursor.execute("""
                INSERT INTO metas_ahorro(usuario_id,monto_meta,mes)
                VALUES(%s,%s,%s)
            """, (session['usuario_id'], monto, mes))

        db.commit()
        flash("Meta guardada", "success")
        return redirect('/estadisticas')

    return render_template("meta.html")

# ===================== ESTADÍSTICAS ======================
@app.route('/estadisticas')
def estadisticas():
    if 'usuario_id' not in session:
        return redirect('/login')

    usuario = session.get('nombre')
    mes = datetime.now().strftime('%Y-%m')

    # -------- Gastos por categoría --------
    cursor.execute("""
        SELECT categoria, SUM(monto) AS total
        FROM gastos
        WHERE usuario_id=%s
        GROUP BY categoria
    """, (session['usuario_id'],))
    gastos_categoria = cursor.fetchall()

    # -------- Gastos por mes --------
    cursor.execute("""
        SELECT DATE_FORMAT(fecha,'%Y-%m') AS mes, SUM(monto) AS total
        FROM gastos
        WHERE usuario_id=%s
        GROUP BY mes
        ORDER BY mes
    """, (session['usuario_id'],))
    gastos_mes = cursor.fetchall()

    # -------- Meta del mes --------
    cursor.execute("""
        SELECT monto_meta FROM metas_ahorro
        WHERE usuario_id=%s AND mes=%s
    """, (session['usuario_id'], mes))
    fila = cursor.fetchone()
    meta = float(fila['monto_meta']) if fila else 0

    # -------- Gasto mensual --------
    cursor.execute("""
        SELECT SUM(monto) AS total
        FROM gastos
        WHERE usuario_id=%s AND DATE_FORMAT(fecha,'%Y-%m')=%s
    """, (session['usuario_id'], mes))
    gasto_mes = float(cursor.fetchone()['total'] or 0)

    # -------- Ingreso mensual --------
    cursor.execute("""
        SELECT SUM(monto) AS total
        FROM ingresos
        WHERE usuario_id=%s AND DATE_FORMAT(fecha,'%Y-%m')=%s
    """, (session['usuario_id'], mes))
    ingreso_mes = float(cursor.fetchone()['total'] or 0)

    # -------- Ahorro real --------
    ahorro_real = ingreso_mes - gasto_mes

    return render_template(
        "estadisticas.html",
        usuario=usuario,
        gastos_categoria=gastos_categoria,
        gastos_mes=gastos_mes,
        meta=meta,
        gasto_mes=gasto_mes,
        ingreso_mes=ingreso_mes,
        ahorro_real=ahorro_real
    )


# ===================== INGRESOS ======================
@app.route('/ingresos/registrar', methods=['GET','POST'])
def registrar_ingreso():
    if 'usuario_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO ingresos(usuario_id, monto, descripcion)
            VALUES(%s, %s, %s)
        """, (session['usuario_id'],
              request.form['monto'],
              request.form['descripcion']))
        db.commit()
        flash("✅ Ingreso registrado correctamente", "success")
        return redirect('/ingresos')

    return render_template('ingreso.html')

# ===================== LISTAR INGRESOS ======================
@app.route('/ingresos')
def listar_ingresos():
    if 'usuario_id' not in session:
        return redirect('/login')

    cursor.execute("""
        SELECT * FROM ingresos WHERE usuario_id=%s ORDER BY fecha DESC
    """, (session['usuario_id'],))
    ingresos = cursor.fetchall()

    cursor.execute("""
        SELECT SUM(monto) AS total FROM ingresos WHERE usuario_id=%s
    """, (session['usuario_id'],))
    total = cursor.fetchone()['total'] or 0

    return render_template('ingresos_lista.html', ingresos=ingresos, total=total)


# ===================== LOGOUT ======================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ===================== RUN ======================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
