from flask import Flask, render_template, request, redirect
import mysql.connector

app = Flask(__name__)

# Conexión a MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Iece5728",
    database="ahorrosdb"
)
cursor = db.cursor()

# Ruta  registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        telefono = request.form['telefono']
        dni = request.form['dni']

        # Insertar en la base de datos
        cursor.execute(
            "INSERT INTO usuarios (nombre, correo, contrasena, telefono, dni) VALUES (%s,%s,%s,%s,%s)",
            (nombre, correo, contrasena, telefono, dni)
        )
        db.commit()
        return "Usuario registrado correctamente. <a href='/login'>Ir a login</a>"

    return render_template('registro.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)