from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime

# POO y FUNCIONAL
from modelos import Usuario, Gasto, AnalizadorGastos
from funciones import promedio_gastos

app = Flask(__name__)
app.secret_key = "clave_secreta_123"

DB_NAME = "ahorrosdb"
DB_USER = "root"
DB_PASS = "Root2003"
DB_HOST = "localhost"


def crear_base_y_tablas():
    """
    Crea la base de datos (si no existe) y las tablas necesarias.
    Devuelve la conexión abierta a la BD (conn).
    """
    # 1) conectar sin DB para crearla si hace falta
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()
    try:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET 'utf8mb4'")
        conn.commit()
        print(f"✔ Base de datos '{DB_NAME}' verificada/creada correctamente.")
    except mysql.connector.Error as err:
        print("❌ Error creando base de datos:", err)
    finally:
        cur.close()
        conn.close()

    # 2) volver a conectar ya seleccionando la DB
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cur = conn.cursor()
    tablas = {
        'usuarios': """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100),
                correo VARCHAR(100),
                contrasena VARCHAR(200),
                telefono VARCHAR(20),
                dni VARCHAR(20),
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        'gastos': """
            CREATE TABLE IF NOT EXISTS gastos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT,
                monto DECIMAL(10,2),
                categoria VARCHAR(100),
                descripcion TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        'ingresos': """
            CREATE TABLE IF NOT EXISTS ingresos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT,
                monto DECIMAL(10,2),
                descripcion TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        'metas_ahorro': """
            CREATE TABLE IF NOT EXISTS metas_ahorro (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT,
                monto_meta DECIMAL(10,2),
                mes VARCHAR(7),
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        'categorias': """
            CREATE TABLE IF NOT EXISTS categorias (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    }

    for name, ddl in tablas.items():
        try:
            cur.execute(ddl)
            print(f"✔ Tabla '{name}' verificada/creada.")
        except mysql.connector.Error as err:
            print(f"❌ Error creando tabla {name}: {err}")

    conn.commit()
    cur.close()
    return conn


# Crear DB y tablas al inicio y obtener conexión (global)
db = crear_base_y_tablas()
# cursor global que usamos en handlers (dictionary=True para dicts)
cursor = db.cursor(dictionary=True)


# ===================== REGISTRO ======================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        datos = (
            request.form['nombre'],
            request.form['correo'],
            request.form['contrasena'],
            request.form.get('telefono', ''),
            request.form.get('dni', '')
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
            flash(f"Bienvenido {usuario.nombre}", "success")
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
    if 'usuario_id' not in session:
        return redirect('/login')

    cursor.execute("SELECT * FROM gastos WHERE usuario_id=%s ORDER BY fecha DESC",
                   (session['usuario_id'],))
    gastos = cursor.fetchall() or []

    cursor.execute("SELECT IFNULL(SUM(monto),0) AS total FROM gastos WHERE usuario_id=%s",
                   (session['usuario_id'],))
    total_row = cursor.fetchone()
    total = float(total_row['total']) if total_row and total_row.get('total') is not None else 0.0

    return render_template("gastos_lista.html", gastos=gastos, total=total)


@app.route('/gastos/registrar', methods=['GET', 'POST'])
def registrar_gasto():
    if 'usuario_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        categoria_val = request.form.get('categoria') or request.form.get('categoria_id') or ''
        cursor.execute("""
            INSERT INTO gastos(usuario_id,monto,categoria,descripcion)
            VALUES(%s,%s,%s,%s)
        """, (session['usuario_id'],
              request.form['monto'],
              categoria_val,
              request.form.get('descripcion', '')))
        db.commit()
        flash("Gasto registrado", "success")
        return redirect('/gastos')

    # Obtener categorías para mostrar en select (si las usas)
    cursor.execute("SELECT id, nombre FROM categorias ORDER BY nombre")
    categorias = cursor.fetchall() or []
    return render_template("registrar_gasto.html", categorias=categorias)


@app.route('/gastos/eliminar/<int:id>')
def eliminar_gasto(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    cursor.execute("DELETE FROM gastos WHERE id=%s AND usuario_id=%s",
                   (id, session['usuario_id']))
    db.commit()
    flash("Gasto eliminado", "danger")
    return redirect('/gastos')


# ===================== META ======================
@app.route('/meta', methods=['GET', 'POST'])
def meta():
    if 'usuario_id' not in session:
        return redirect('/login')

    mes = datetime.now().strftime('%Y-%m')

    if request.method == 'POST':
        monto = request.form['monto_meta']
        # si quieren, validar que monto sea float
        try:
            monto_val = float(monto)
        except:
            flash("Ingrese un monto válido", "danger")
            return redirect('/meta')

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
            """, (monto_val, session['usuario_id'], mes))
        else:
            cursor.execute("""
                INSERT INTO metas_ahorro(usuario_id,monto_meta,mes)
                VALUES(%s,%s,%s)
            """, (session['usuario_id'], monto_val, mes))

        db.commit()
        flash("Meta guardada", "success")
        return redirect('/estadisticas')

    # si GET, mostrar la vista (tu template meta.html asumido)
    # intentar obtener meta actual para mostrar en formulario si existe
    cursor.execute("""
        SELECT monto_meta FROM metas_ahorro
        WHERE usuario_id=%s AND mes=%s
        LIMIT 1
    """, (session['usuario_id'], mes))
    fila = cursor.fetchone()
    meta_val = float(fila['monto_meta']) if fila and fila.get('monto_meta') is not None else 0.0

    # calcular ahorro real del mes para mostrar en la vista
    cursor.execute("""
        SELECT IFNULL(SUM(monto),0) AS total FROM ingresos
        WHERE usuario_id=%s AND DATE_FORMAT(fecha,'%%Y-%%m')=%s
    """, (session['usuario_id'], mes))
    ingreso_mes = float(cursor.fetchone()['total'] or 0)

    cursor.execute("""
        SELECT IFNULL(SUM(monto),0) AS total FROM gastos
        WHERE usuario_id=%s AND DATE_FORMAT(fecha,'%%Y-%%m')=%s
    """, (session['usuario_id'], mes))
    gasto_mes = float(cursor.fetchone()['total'] or 0)

    ahorro_real = ingreso_mes - gasto_mes
    progreso = round(min(100.0, (ahorro_real / meta_val) * 100.0), 2) if meta_val > 0 else 0.0

    return render_template("meta.html", meta=meta_val, ahorro_real=ahorro_real, progreso=progreso)


# ===================== ESTADÍSTICAS ======================
@app.route('/estadisticas')
def estadisticas():
    if 'usuario_id' not in session:
        return redirect('/login')

    usuario_id = session['usuario_id']
    usuario = session.get('nombre')

    now = datetime.now()
    anio_actual = now.year
    mes_actual = now.month

    # -------------------------------
    # Fechas para mes actual (rango)
    # -------------------------------
    primer_dia_mes = datetime(anio_actual, mes_actual, 1)
    if mes_actual == 12:
        primer_dia_siguiente_mes = datetime(anio_actual + 1, 1, 1)
    else:
        primer_dia_siguiente_mes = datetime(anio_actual, mes_actual + 1, 1)

    # -------------------------------
    # Gastos por categoría
    # -------------------------------
    cursor.execute("""
        SELECT categoria, IFNULL(SUM(monto),0) AS total
        FROM gastos
        WHERE usuario_id=%s
        GROUP BY categoria
        ORDER BY total DESC
    """, (usuario_id,))
    gastos_categoria = cursor.fetchall() or []

    # -------------------------------
    # Totales del mes usando rango de fechas
    # -------------------------------
    cursor.execute("""
        SELECT IFNULL(SUM(monto),0) AS total
        FROM ingresos
        WHERE usuario_id=%s AND fecha >= %s AND fecha < %s
    """, (usuario_id, primer_dia_mes, primer_dia_siguiente_mes))
    ingreso_mes = float(cursor.fetchone()['total'] or 0)

    cursor.execute("""
        SELECT IFNULL(SUM(monto),0) AS total
        FROM gastos
        WHERE usuario_id=%s AND fecha >= %s AND fecha < %s
    """, (usuario_id, primer_dia_mes, primer_dia_siguiente_mes))
    gasto_mes = float(cursor.fetchone()['total'] or 0)

    ahorro_real = ingreso_mes - gasto_mes

    # -------------------------------
    # Meta del mes
    # -------------------------------
    mes_str = primer_dia_mes.strftime('%Y-%m')
    cursor.execute("""
        SELECT monto_meta FROM metas_ahorro
        WHERE usuario_id=%s AND mes=%s
        LIMIT 1
    """, (usuario_id, mes_str))
    fila = cursor.fetchone()
    meta = float(fila['monto_meta']) if fila and fila.get('monto_meta') is not None else 0.0
    progreso_meta = round(min(100.0, (ahorro_real / meta) * 100.0), 2) if meta > 0 else 0.0

    # -------------------------------
    # Totales históricos
    # -------------------------------
    cursor.execute("""
        SELECT IFNULL(SUM(monto),0) AS total
        FROM ingresos
        WHERE usuario_id=%s
    """, (usuario_id,))
    total_ingresos = float(cursor.fetchone()['total'] or 0)

    cursor.execute("""
        SELECT IFNULL(SUM(monto),0) AS total
        FROM gastos
        WHERE usuario_id=%s
    """, (usuario_id,))
    total_gastos = float(cursor.fetchone()['total'] or 0)

    # -------------------------------
    # Totales por mes para gráficas
    # -------------------------------
    cursor.execute("""
        SELECT MONTH(fecha) AS mes_num, IFNULL(SUM(monto),0) AS total
        FROM ingresos
        WHERE usuario_id=%s AND YEAR(fecha) = %s
        GROUP BY MONTH(fecha)
    """, (usuario_id, anio_actual))
    filas_ing = cursor.fetchall() or []

    cursor.execute("""
        SELECT MONTH(fecha) AS mes_num, IFNULL(SUM(monto),0) AS total
        FROM gastos
        WHERE usuario_id=%s AND YEAR(fecha) = %s
        GROUP BY MONTH(fecha)
    """, (usuario_id, anio_actual))
    filas_gas = cursor.fetchall() or []

    ing_por_mes_map = {int(r['mes_num']): float(r['total']) for r in filas_ing}
    gas_por_mes_map = {int(r['mes_num']): float(r['total']) for r in filas_gas}

    month_labels = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
    ingresos_por_mes = [ing_por_mes_map.get(m, 0.0) for m in range(1, 13)]
    gastos_por_mes = [gas_por_mes_map.get(m, 0.0) for m in range(1, 13)]

    # -------------------------------
    # Renderizado del template
    # -------------------------------
    return render_template(
        "estadisticas.html",
        usuario=usuario,
        ingreso_mes=ingreso_mes,
        gasto_mes=gasto_mes,
        ahorro_real=ahorro_real,
        meta=meta,
        progreso_meta=progreso_meta,
        gastos_categoria=gastos_categoria,
        total_ingresos=total_ingresos,
        total_gastos=total_gastos,
        month_labels=month_labels,
        ingresos_por_mes=ingresos_por_mes,
        gastos_por_mes=gastos_por_mes,
        now=now
    )

# ===================== GUARDAR META ======================
@app.route('/guardar_meta', methods=['POST'])
def guardar_meta():
    if 'usuario_id' not in session:
        return redirect('/login')

    monto = request.form.get('monto_meta')  # <-- usar .get() evita KeyError
    if not monto:
        flash("No se recibió el monto de la meta", "danger")
        return redirect('/meta')

    try:
        monto_val = float(monto)
    except ValueError:
        flash("Ingrese un monto válido", "danger")
        return redirect('/meta')

    mes = datetime.now().strftime('%Y-%m')
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
        """, (monto_val, session['usuario_id'], mes))
    else:
        cursor.execute("""
            INSERT INTO metas_ahorro(usuario_id,monto_meta,mes)
            VALUES(%s,%s,%s)
        """, (session['usuario_id'], monto_val, mes))

    db.commit()
    flash("Meta guardada correctamente", "success")
    return redirect('/estadisticas')

# ===================== INGRESOS ======================
@app.route('/ingresos/registrar', methods=['GET', 'POST'])
def registrar_ingreso():
    if 'usuario_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO ingresos(usuario_id, monto, descripcion)
            VALUES(%s, %s, %s)
        """, (session['usuario_id'],
              request.form['monto'],
              request.form.get('descripcion', '')))
        db.commit()
        flash("Ingreso registrado correctamente", "success")
        return redirect('/ingresos')

    # renderiza formulario de nuevo ingreso (ingresos_nuevo.html)
    return render_template('ingresos_nuevo.html')


@app.route('/ingresos')
def listar_ingresos():
    if 'usuario_id' not in session:
        return redirect('/login')

    cursor.execute("""SELECT * FROM ingresos WHERE usuario_id=%s ORDER BY fecha DESC""",
                   (session['usuario_id'],))
    ingresos = cursor.fetchall() or []

    cursor.execute("""SELECT IFNULL(SUM(monto),0) AS total FROM ingresos WHERE usuario_id=%s""",
                   (session['usuario_id'],))
    total_row = cursor.fetchone()
    total = float(total_row['total']) if total_row and total_row.get('total') is not None else 0.0

    return render_template('ingresos_lista.html', ingresos=ingresos, total=total)


# ===================== LOGOUT ======================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ===================== RUN ======================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
