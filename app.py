#Flask application for agricultural machinery maintenance management

# Import necessary libraries for basic Flask functionality
from flask import Flask, render_template, make_response

# Secure handling and making HTTP requests, manage database connections and secure file uploads
from flask import request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import sqlite3, requests # Direct SQLite3 usage
import os

# Generate PDF reports
import pdfkit

# Import necessary libraries for date and time handling and making HTTP requests
from datetime import datetime

# Initialize the Flask application and configure upload folders
app = Flask(__name__)

app.secret_key = 'elorza'

UPLOAD_FOLDER_MAQUINAS = 'static/fotos/maquinas'
UPLOAD_FOLDER_COMPONENTES = 'static/fotos/componentes'

os.makedirs(UPLOAD_FOLDER_MAQUINAS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_COMPONENTES, exist_ok=True)

app.config['UPLOAD_FOLDER_MAQUINAS'] = 'static/fotos/maquinas'
app.config['UPLOAD_FOLDER_COMPONENTES'] = 'static/fotos/componentes'

# Initialize the SQLite database
def get_db_connection():
    conn = sqlite3.connect('mantenimiento_agricola.db')
    conn.row_factory = sqlite3.Row
    return conn

# Home Page
@app.route('/')
def index():
    conn = get_db_connection()
    maquinas = conn.execute('SELECT * FROM maquinas').fetchall()
    conn.close()
    return render_template('index.html', maquinas=maquinas)

# Photo Upload
# Define allowed file extensions for image uploads
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# This route allows users to upload a photo for a specific machine.
@app.route('/upload_foto/<int:id>', methods=['POST'])
def upload_foto_maquina(id):
    if 'foto' not in request.files:
        return redirect(url_for('vista_maquina', id=id))
    # Check if the file is present in the request
    foto = request.files['foto']
    if foto.filename == '':
        return redirect(url_for('vista_maquina', id=id))
    # Check if the file is allowed
    if foto and allowed_file(foto.filename):
        # Guardar foto como "maquina_<id>.ext"
        extension = foto.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"maquina_{id}.{extension}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER_MAQUINAS'], filename)
        foto.save(filepath)
        # Actualizar la base de datos con el nombre de la foto
        conn = get_db_connection()
        conn.execute('UPDATE maquinas SET Foto = ? WHERE ID = ?', (filename, id))
        conn.commit()
        conn.close()
    return redirect(url_for('vista_maquina', id=id))

# This route allows users to upload a photo for a specific component.
@app.route('/upload_foto_componente/<int:id>', methods=['POST'])
def upload_foto_componente(id):
    if 'foto' not in request.files:
        return redirect(url_for('vista_componente', id=id))
    foto = request.files['foto']
    if foto.filename == '':
        return redirect(url_for('vista_componente', id=id))
    # Guardar foto como "componente_<id>.ext"
    if foto and allowed_file(foto.filename):
        extension = foto.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"componente_{id}.{extension}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER_COMPONENTES'], filename)
        foto.save(filepath)
        # Guardar el nombre del archivo en la base de datos
        conn = get_db_connection()
        conn.execute('UPDATE componentes SET Foto = ? WHERE rowid = ?', (filename, id))
        conn.commit()
        conn.close()
    return redirect(url_for('vista_componente', id=id))
# The image is saved in the 'static/fotos' directory.

# Machine Registration
# This route allows users to register a new machine with its details and photo.
@app.route('/maquinas/nueva', methods=['GET', 'POST'])
def registrar_maquina():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        componentes = conn.execute('SELECT * FROM componentes').fetchall()
        # Datos máquina
        codigo = request.form['codigo']
        nombre = request.form['nombre']
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        anio = request.form.get('anio')
        estado = request.form.get('estado')
        observaciones = request.form.get('observaciones')
        foto = request.files.get('foto')
        # Foto opcional
        foto_filename = None
        if foto and foto.filename != '':
            foto_filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER_MAQUINAS'], foto_filename))
        # Verificar si el código ya existe
        ya_existe = cursor.execute('SELECT 1 FROM maquinas WHERE Codigo = ?', (codigo,)).fetchone()
        if ya_existe:
            flash('Ya existe una máquina con ese código.')
            return redirect(url_for('registrar_maquina'))
        # Insertar máquina en la base de datos
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO maquinas (Codigo, Nombre, Marca, Modelo, Año, Estado, Observaciones, Foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (codigo, nombre, marca, modelo, anio, estado, observaciones, foto_filename))
        id_maquina = cursor.lastrowid
        # Componentes seleccionados
        componentes_seleccionados = request.form.getlist('componentes_seleccionados')
        # Asociar componentes a la máquina
        for id_componente in componentes_seleccionados:
            cursor.execute('''
                INSERT INTO maquinas_componentes (ID_Maquina, ID_Componente)
                VALUES (?, ?)
            ''', (id_maquina, id_componente))
            # Obtener datos de frecuencia
            frecuencia = request.form.get(f'frecuencia_{id_componente}')
            unidad = request.form.get(f'unidad_{id_componente}')
            criterio = request.form.get(f'criterio_{id_componente}')
            # Insertar frecuencia si frecuencia y unidad están presentes y frecuencia > 0
            if frecuencia and unidad and frecuencia.isdigit() and int(frecuencia) > 0:
                cursor.execute('''
                    INSERT INTO frecuencias (ID_Maquina, ID_Componente, Frecuencia, "Unidad tiempo", "Criterio adicional")
                    VALUES (?, ?, ?, ?, ?)
                ''', (id_maquina, id_componente, int(frecuencia), unidad, criterio))

        conn.commit()
        conn.close()
        return redirect(url_for('vista_maquina', id=id_maquina))

    # GET: mostrar formulario
    conn = get_db_connection()
    componentes = conn.execute('SELECT * FROM componentes').fetchall()
    conn.close()
    return render_template('registrar_maquina.html', componentes=componentes)


# Machinery Management
# The machinery management system allows users to view the list of machines and their details.
@app.route('/maquinas')
def lista_maquinas():
    conn = get_db_connection()
    maquinas = conn.execute('SELECT * FROM maquinas').fetchall()
    conn.close()
    return render_template('maquinas.html', maquinas=maquinas)

# Machine Details
# This route retrieves the details of a specific machine by its ID and displays its components and frequencies
@app.route('/maquina/<int:id>')
def vista_maquina(id):
    conn = get_db_connection()
    maquina = conn.execute('SELECT * FROM maquinas WHERE ID = ?', (id,)).fetchone()
    
    # Obtener componentes asociados a la máquina con sus frecuencias
    componentes_asociados = conn.execute('''
        SELECT c.*, f.Frecuencia, f."Unidad tiempo", f."Criterio adicional"
        FROM componentes c
        JOIN maquinas_componentes mc ON c.ID = mc.ID_Componente
        LEFT JOIN frecuencias f ON c.ID = f.ID_Componente AND mc.ID_Maquina = f.ID_Maquina
        WHERE mc.ID_Maquina = ?
    ''', (id,)).fetchall()

    # Componentes no asociados
    componentes_disponibles = conn.execute('''
        SELECT * FROM componentes
        WHERE ID_Componente NOT IN (
            SELECT ID_Componente FROM maquinas_componentes WHERE ID_Maquina = ?
        )
    ''', (id,)).fetchall()

    conn.close()
    return render_template('maquina.html', maquina=maquina,
        componentes_asociados=componentes_asociados,
        componentes_no_asociados=componentes_disponibles)

# Machine Editing
# This route allows users to edit the details of an existing machine.
@app.route('/maquina/<int:id>/editar', methods=['GET', 'POST'])
def editar_maquina(id):
    conn = get_db_connection()
    maquina = conn.execute('SELECT * FROM maquinas WHERE ID = ?', (id,)).fetchone()

    if not maquina:
        conn.close()
        return render_template('404.html', message="Máquina no encontrada"), 404

    if request.method == 'POST':
        nombre = request.form['nombre']
        marca = request.form['marca']
        modelo = request.form['modelo']
        anio = request.form['anio']
        estado = request.form['estado']
        observaciones = request.form['observaciones']

        conn.execute('''
            UPDATE maquinas SET Nombre = ?, Marca = ?, Modelo = ?, Año = ?, Estado = ?, Observaciones = ?
            WHERE ID = ?
        ''', (nombre, marca, modelo, anio, estado, observaciones, id))
        conn.commit()
        conn.close()
        return redirect(url_for('vista_maquina', id=id))

    conn.close()
    return render_template('editar_maquina.html', maquina=maquina)

# Frequency Management
# The frequency management system allows users to register and edit maintenance frequencies for components of a machine.
@app.route('/maquina/<int:id_maquina>/asignar_componente', methods=['GET', 'POST'])
def asignar_componente(id_maquina):
    conn = get_db_connection()
    mensaje_error = None
    try:
        componentes = conn.execute('SELECT * FROM componentes').fetchall()
        # Obtener componentes asociados a la máquina
        asociados = conn.execute('''
            SELECT ID_Componente FROM maquinas_componentes
            WHERE ID_Maquina = ?
        ''', (id_maquina,)).fetchall()
        # Convertir a un set para verificar rápidamente
        ids_asociados = {a['ID_Componente'] for a in asociados}
        # Si el método es POST, procesar la asignación
        if request.method == 'POST':
            id_componente = int(request.form['componente'])
            # Verificar si el componente ya está asociado a la máquina
            if id_componente in ids_asociados:
                mensaje_error = "Este componente ya está asignado a esta máquina."
            else:
                frecuencia = request.form['frecuencia']
                unidad = request.form['unidad_tiempo']
                criterio = request.form.get('criterio_adicional', '')
                # Insertar el componente en la relación muchos a muchos
                conn.execute('''
                    INSERT INTO maquinas_componentes (ID_Maquina, ID_Componente)
                    VALUES (?, ?)
                ''', (id_maquina, id_componente))
                # Insertar la frecuencia si es válida
                if frecuencia and unidad and frecuencia.isdigit() and int(frecuencia) > 0:
                    conn.execute('''
                        INSERT INTO frecuencias (ID_Maquina, ID_Componente, Frecuencia, "Unidad tiempo", "Criterio adicional")
                        VALUES (?, ?, ?, ?, ?)
                    ''', (id_maquina, id_componente, int(frecuencia), unidad, criterio))
                # Confirmar cambios
                conn.commit()
                # Redirigir a la vista de la máquina
                return redirect(url_for('vista_maquina', id=id_maquina))
    finally:
        # Cerrar la conexión a la base de datos
        conn.close()
    # Si es GET, mostrar el formulario
    return render_template('asignar_componente.html', id_maquina=id_maquina, componentes=componentes, mensaje_error=mensaje_error)

# Frequency Editing
# This route allows users to edit the frequency of a specific component for a machine.
@app.route('/maquina/<int:id_maquina>/frecuencia/<int:id_componente>', methods=['GET', 'POST'])
def editar_frecuencia(id_maquina, id_componente):
    conn = get_db_connection()
    
    # Obtener frecuencia actual si existe
    frecuencia = conn.execute('''
        SELECT * FROM frecuencias WHERE ID_Maquina = ? AND ID_Componente = ?
    ''', (id_maquina, id_componente)).fetchone()
    
    if request.method == 'POST':
        nueva_frecuencia = request.form['frecuencia']
        unidad_tiempo = request.form['unidad_tiempo']
        criterio_adicional = request.form.get('criterio_adicional', '')

        cursor = conn.cursor()

        if frecuencia:
            # Actualizar registro existente
            cursor.execute('''
                UPDATE frecuencias
                SET Frecuencia = ?, "Unidad tiempo" = ?, "Criterio adicional" = ?
                WHERE ID_Maquina = ? AND ID_Componente = ?
            ''', (nueva_frecuencia, unidad_tiempo, criterio_adicional, id_maquina, id_componente))
        else:
            # Insertar nuevo registro
            cursor.execute('''
                INSERT INTO frecuencias (ID_Maquina, ID_Componente, Frecuencia, "Unidad tiempo", "Criterio adicional")
                VALUES (?, ?, ?, ?, ?)
            ''', (id_maquina, id_componente, nueva_frecuencia, unidad_tiempo, criterio_adicional))
        
        # Redirigir a la vista de la máquina
        conn.commit()
        conn.close()
        return redirect(url_for('vista_maquina', id=id_maquina))
    
    conn.close()
    return render_template('editar_frecuencia.html', frecuencia=frecuencia, id_maquina=id_maquina, id_componente=id_componente)

# Component Management
# The component management system allows users to view the list of components and their details.
# TODO: Implement component editing and deletion functionality.
@app.route('/componentes')
def lista_componentes():
    conn = get_db_connection()
    componentes = conn.execute('SELECT * FROM componentes').fetchall()
    conn.close()
    return render_template('componentes.html', componentes=componentes) 

# Component Registration
# This route allows users to register a new component with its details and photo.
@app.route('/componentes/nuevo', methods=['GET', 'POST'])
def registrar_componente():
    # If the request is POST, process the form data
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        tipo = request.form['tipo']
        foto = request.files.get('foto')

        foto_filename = None
        if foto and foto.filename != '':
            foto_filename = secure_filename(foto.filename)
            ruta = os.path.join('static', 'fotos', 'componentes', foto_filename)
            foto.save(ruta)

        # Guardar en base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO componentes (ID_Componente, Nombre, Descripcion, Tipo, Foto) VALUES (?, ?, ?, ?, ?)''', (codigo, nombre, descripcion, tipo, foto_filename))
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return redirect(url_for('vista_componente', id=nuevo_id))
    # If the request is GET, render the form
    return render_template('registrar_componente.html')

# Component Details
# This route allows users to view the details of a specific component, including its suppliers and frequencies
@app.route('/componente/<int:id>')
def vista_componente(id):
    conn = get_db_connection()
    componente = conn.execute('SELECT * FROM componentes WHERE ID = ?', (id,)).fetchone()

    if componente is None:
        conn.close()
        return render_template('404.html', message="Componente no encontrado"), 404

    proveedores = conn.execute('''
        SELECT p.*
        FROM proveedores p
        JOIN componentes_proveedores cp ON p.ID = cp.ID_Proveedor
        WHERE cp.ID_Componente = ?
    ''', (componente['ID'],)).fetchall()

    conn.close()
    return render_template('componente.html', componente=componente, proveedores=proveedores)

# Stock Management
# The stock is calculated based on the entries and exits recorded in the database.
# The stock is displayed in a table with the component name and the current stock level.
def obtener_stock_actual():
    conn = get_db_connection()
    consulta = '''
    SELECT c.ID_Componente, c.Nombre,
           IFNULL(SUM(CASE WHEN s.Tipo = 'entrada' THEN s.Cantidad ELSE 0 END), 0) -
           IFNULL(SUM(CASE WHEN s.Tipo = 'salida' THEN s.Cantidad ELSE 0 END), 0) AS Stock_Actual
    FROM componentes c
    LEFT JOIN stock s ON c.ID_Componente = s.ID_Componente
    GROUP BY c.ID_Componente
    '''
    resultado = conn.execute(consulta).fetchall()
    conn.close()
    return resultado

# Stock Registration
# The stock management system allows users to register stock entries and exits for components.
# It also provides a form to register stock entries or exits.
@app.route('/registrar_stock', methods=['GET', 'POST'])
def registrar_stock():
    conn = get_db_connection()
    componentes = conn.execute('SELECT ID_Componente, Nombre FROM componentes').fetchall()

    if request.method == 'POST':
        id_componente = request.form['id_componente']
        cantidad = int(request.form['cantidad'])
        tipo = request.form['tipo']
        observacion = request.form['observacion']

        conn.execute('''
            INSERT INTO stock (ID_Componente, Cantidad, Tipo, Observacion)
            VALUES (?, ?, ?, ?)
        ''', (id_componente, cantidad, tipo, observacion))
        conn.commit()
        conn.close()
        return redirect(url_for('vista_stock'))

    conn.close()
    return render_template('registrar_stock.html', componentes=componentes)

# Stock View
# The stock view system allows users to view the current stock of components.
@app.route('/stock')
def vista_stock():
    stock = obtener_stock_actual()
    return render_template('stock.html', stock=stock)

# Component Purchase
# The component purchase system allows users to register purchases of components from providers.
@app.route('/registrar_compra', methods=['GET', 'POST'])
def registrar_compra():
    conn = get_db_connection()
    proveedores = conn.execute('SELECT ID, Nombre FROM proveedores').fetchall()
    componentes = conn.execute('SELECT ID, Nombre FROM componentes').fetchall()

    if request.method == 'POST':
        proveedor = request.form['proveedor']
        componente = request.form['componente']
        cantidad = int(request.form['cantidad'])
        precio_unitario = float(request.form['precio_unitario'])
        observacion = request.form['observacion']

        # Insertar en compras
        conn.execute('''
            INSERT INTO compras (ID_Proveedor, ID_Componente, Cantidad, Precio_Unitario, Observacion)
            VALUES (?, ?, ?, ?, ?)
        ''', (proveedor, componente, cantidad, precio_unitario, observacion))

        # También insertar en stock como entrada
        conn.execute('''
            INSERT INTO stock (ID_Componente, Cantidad, Tipo, Observacion)
            VALUES (?, ?, 'entrada', ?)
        ''', (componente, cantidad, f'Compra de proveedor {proveedor}: {observacion}'))

        conn.commit()
        conn.close()
        return redirect(url_for('vista_stock'))

    conn.close()
    return render_template('registrar_compra.html', proveedores=proveedores, componentes=componentes)

# Component Deletion
# The component deletion system allows users to delete components from the database.
@app.route('/componentes/eliminar/<int:id>', methods=['POST'])
def eliminar_componente(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM componentes WHERE ID = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('lista_componentes'))

# Provider Management
# The provider management system allows users to view the list of providers and their details.
@app.route('/proveedores')
def listar_proveedores():
    conn = get_db_connection()
    proveedores = conn.execute('SELECT * FROM proveedores').fetchall()
    conn.close()
    return render_template('proveedores.html', proveedores=proveedores)

# Provider Registration
@app.route('/proveedores/agregar', methods=['POST'])
def agregar_proveedor():
    nombre = request.form['nombre']
    localidad = request.form.get('localidad', '')
    contacto = request.form.get('contacto', '')
    telefono = request.form.get('telefono', '')
    email = request.form.get('email', '')
    rubro = request.form.get('rubro', '')
    direccion = request.form.get('direccion', '')
    observaciones = request.form.get('observaciones', '')

    if not nombre.strip():
        flash('El nombre es obligatorio.')
        return redirect(url_for('listar_proveedores'))

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO proveedores (Nombre, Localidad, Contacto, Telefono, Email, Rubro, Direccion, Observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nombre, localidad, contacto, telefono, email, rubro, direccion, observaciones))
    conn.commit()
    conn.close()

    flash(f'Proveedor "{nombre}" agregado correctamente.')
    return redirect(url_for('listar_proveedores'))

# View Provider
@app.route('/proveedores/<int:id>')
def ver_proveedor(id):
    conn = get_db_connection()
    proveedor = conn.execute('SELECT * FROM proveedores WHERE ID = ?', (id,)).fetchone()
    conn.close()
    if proveedor is None:
        flash('Proveedor no encontrado.')
        return redirect(url_for('listar_proveedores'))
    return render_template('ver_proveedor.html', proveedor=proveedor)

# Edit Provider
@app.route('/proveedores/<int:id>/editar', methods=['GET', 'POST'])
def editar_proveedor(id):
    conn = get_db_connection()
    proveedor = conn.execute('SELECT * FROM proveedores WHERE ID = ?', (id,)).fetchone()
    if proveedor is None:
        conn.close()
        flash('Proveedor no encontrado.')
        return redirect(url_for('listar_proveedores'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        localidad = request.form.get('localidad', '')
        contacto = request.form.get('contacto', '')
        telefono = request.form.get('telefono', '')
        email = request.form.get('email', '')
        rubro = request.form.get('rubro', '')
        direccion = request.form.get('direccion', '')
        observaciones = request.form.get('observaciones', '')

        if not nombre.strip():
            flash('El nombre es obligatorio.')
            conn.close()
            return redirect(url_for('editar_proveedor', id=id))

        conn.execute('''
            UPDATE proveedores SET
            Nombre = ?, Localidad = ?, Contacto = ?, Telefono = ?, Email = ?, Rubro = ?, Direccion = ?, Observaciones = ?
            WHERE ID = ?
        ''', (nombre, localidad, contacto, telefono, email, rubro, direccion, observaciones, id))
        conn.commit()
        conn.close()

        flash(f'Proveedor "{nombre}" actualizado correctamente.')
        return redirect(url_for('listar_proveedores'))

    conn.close()
    return render_template('editar_proveedor.html', proveedor=proveedor)

# Delete Provider
@app.route('/proveedores/<int:id>/eliminar', methods=['POST'])
def eliminar_proveedor(id):
    conn = get_db_connection()
    proveedor = conn.execute('SELECT * FROM proveedores WHERE ID = ?', (id,)).fetchone()
    if proveedor is None:
        conn.close()
        flash('Proveedor no encontrado.')
        return redirect(url_for('listar_proveedores'))

    conn.execute('DELETE FROM proveedores WHERE ID = ?', (id,))
    conn.commit()
    conn.close()

    flash(f'Proveedor "{proveedor["Nombre"]}" eliminado correctamente.')
    return redirect(url_for('listar_proveedores'))

# Purchase History
# The purchase history system allows users to view the list of purchases made by the company.
@app.route('/historial_compras')
def historial_compras():
    conn = get_db_connection()
    compras = conn.execute('''
        SELECT co.Fecha, co.ID_Compra, co.Cantidad, co.Precio_Unitario, co.Observacion,
               c.Nombre AS Nombre_Componente,
               p.Nombre AS Nombre_Proveedor
        FROM compras co
        JOIN componentes c ON co.ID_Componente = c.ID
        JOIN proveedores p ON co.ID_Proveedor = p.ID
        ORDER BY co.Fecha DESC
    ''').fetchall()
    conn.close()
    return render_template('historial_compras.html', compras=compras)

# This route retrieves the purchase history and displays it in a table.

@app.route('/historial_compras_complejo', methods=['GET'])
def historial_compras_complejo():
    conn = get_db_connection()

    # Obtener filtros del formulario GET
    proveedor = request.args.get('proveedor', '')
    componente = request.args.get('componente', '')

    # Armar consulta dinámica
    query = '''
        SELECT co.Fecha, co.ID_Compra, co.Cantidad, co.Precio_Unitario, co.Observacion,
               c.Nombre AS Nombre_Componente,
               p.Nombre AS Nombre_Proveedor
        FROM compras co
        JOIN componentes c ON co.ID_Componente = c.ID_Componente
        JOIN proveedores p ON co.ID_Proveedor = p.ID
    '''
    conditions = []
    params = []

    if proveedor:
        conditions.append('p.ID = ?')
        params.append(proveedor)

    if componente:
        conditions.append('c.ID_Componente = ?')
        params.append(componente)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY co.Fecha DESC'

    compras = conn.execute(query, params).fetchall()

    # También cargar combos de filtro
    proveedores = conn.execute('SELECT ID_Proveedor, Nombre FROM proveedores').fetchall()
    componentes = conn.execute('SELECT ID_Componente, Nombre FROM componentes').fetchall()

    conn.close()
    return render_template('historial_compras.html', compras=compras,
                           proveedores=proveedores, componentes=componentes,
                           proveedor_seleccionado=proveedor,
                           componente_seleccionado=componente)

# Payment to Providers
# The payment management system allows users to register payments made to providers.
@app.route('/registrar_pago', methods=['GET', 'POST'])
def registrar_pago():
    conn = get_db_connection()
    proveedores = conn.execute('SELECT ID, Nombre FROM proveedores').fetchall()

    if request.method == 'POST':
        id_proveedor = request.form['proveedor']
        monto = float(request.form['monto'])
        metodo = request.form['metodo']
        observacion = request.form['observacion']

        conn.execute('''
            INSERT INTO pagos_proveedores (ID_Proveedor, Monto, Metodo, Observacion)
            VALUES (?, ?, ?, ?)
        ''', (id_proveedor, monto, metodo, observacion))

        conn.commit()
        conn.close()
        return redirect(url_for('resumen_cuentas'))

    conn.close()
    return render_template('registrar_pago.html', proveedores=proveedores)

# Summary of Accounts
# This route retrieves the summary of accounts for each provider, showing total purchases, total payments,
@app.route('/resumen_cuentas')
def resumen_cuentas():
    conn = get_db_connection()
    resumen = conn.execute('''
        SELECT 
            p.ID, p.Nombre,
        IFNULL((SELECT SUM(c.Cantidad * c.Precio_Unitario) 
                    FROM compras c 
                    WHERE c.ID_Proveedor = p.ID), 0) AS Total_Compras,
        IFNULL((SELECT SUM(pg.Monto) 
                    FROM pagos_proveedores pg 
                    WHERE pg.ID_Proveedor = p.ID), 0) AS Total_Pagos,
        (IFNULL((SELECT SUM(c.Cantidad * c.Precio_Unitario) 
                    FROM compras c 
                    WHERE c.ID_Proveedor = p.ID), 0) - 
        IFNULL((SELECT SUM(pg.Monto) 
                    FROM pagos_proveedores pg 
                    WHERE pg.ID_Proveedor = p.ID), 0)
        ) AS Saldo
    FROM proveedores p
    ORDER BY p.Nombre;
    ''').fetchall()
    conn.close()
    return render_template('resumen_cuentas.html', resumen=resumen)

# Statistics
# The statistics system allows users to view charts and graphs of purchases by provider.
@app.route('/estadisticas/compras_proveedor')
def compras_por_proveedor():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT p.Nombre, SUM(c.Cantidad * c.Precio_Unitario) as Total
        FROM compras c
        JOIN proveedores p ON c.ID_Proveedor = p.ID
        GROUP BY p.ID
        ORDER BY Total DESC
    ''').fetchall()
    conn.close()

    labels = [row['Nombre'] for row in data]
    values = [row['Total'] for row in data]

    return render_template('grafico_compras_proveedor.html', labels=labels, values=values)

# PDF Export
# This route generates a PDF report of the summary of accounts for each provider.
@app.route('/resumen_cuentas/pdf')
def exportar_resumen_pdf():
    conn = get_db_connection()
    resumen = conn.execute('''
        SELECT p.ID, p.Nombre,
            IFNULL(SUM(c.Cantidad * c.Precio_Unitario), 0) AS Total_Compras,
            IFNULL(SUM(pg.Monto), 0) AS Total_Pagos,
            (IFNULL(SUM(c.Cantidad * c.Precio_Unitario), 0) - IFNULL(SUM(pg.Monto), 0)) AS Saldo
        FROM proveedores p
        LEFT JOIN compras c ON p.ID = c.ID_Proveedor
        LEFT JOIN pagos_proveedores pg ON p.ID = pg.ID_Proveedor
        GROUP BY p.ID
    ''').fetchall()
    conn.close()

    rendered = render_template('resumen_pdf.html', resumen=resumen)

    # Si wkhtmltopdf no está en PATH, especificá la ruta
    config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
    pdf = pdfkit.from_string(rendered, False, configuration=config)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=resumen_cuentas.pdf'
    return response

# Config (use environment variables for security)
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"

# Configuración de caché
from flask_caching import Cache
cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 1800  # 30 minutos
})
cache.init_app(app)

# Configuración del clima
app.config['WEATHER_API_KEY'] = os.getenv('WEATHER_API_KEY')
COORDENADAS_UCACHA = {
    'lat': "-33.03203",
    'lon': "-63.50666"
}

@app.route('/api/clima')
@cache.cached(timeout=1800)

# Endpoint API para datos climáticos
# Devuelve JSON con caché de 30 minutos
def api_clima():
    
    try:
        datos = obtener_datos_clima()
        if not datos:
            raise ValueError("Datos climáticos no disponibles")
            
        return jsonify({
            'status': 'success',
            'data': datos,
            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ubicacion': COORDENADAS_UCACHA
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'data': None
        }), 500

def obtener_datos_clima():
    # Obtiene y procesa datos climáticos
    try:
        respuesta = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                **COORDENADAS_UCACHA,
                'appid': app.config['WEATHER_API_KEY'],
                'units': 'metric',
                'lang': 'es'
            },
            timeout=5
        )
        respuesta.raise_for_status()
        
        datos = respuesta.json()
        
        return {
            'temperatura': round(datos['main']['temp']),
            'sensacion_termica': round(datos['main']['feels_like']),
            'condicion': datos['weather'][0]['description'].capitalize(),
            'icono': mapear_icono_clima(datos['weather'][0]['id']),
            'humedad': datos['main']['humidity'],
            'viento_kmh': round(datos['wind']['speed'] * 3.6),
            'presion': datos['main']['pressure'],
            'visibilidad_km': round(datos.get('visibility', 0) / 1000, 1)
        }
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error API Clima: {str(e)}")
        return None

def mapear_icono_clima(weather_id):
    # Mapeo mejorado de iconos climáticos
    iconos = {
        range(200, 300): "bi-lightning",  # Tormentas
        range(300, 400): "bi-cloud-drizzle",  # Llovizna
        range(500, 600): "bi-cloud-rain",  # Lluvia
        range(600, 700): "bi-snow2",  # Nieve
        range(700, 800): "bi-cloud-fog",  # Atmósfera
        800: "bi-sun",  # Despejado
        range(801, 804): "bi-cloud-sun"  # Nubes
    }
    
    for rango, icono in iconos.items():
        if isinstance(rango, range):
            if weather_id in rango:
                return icono
        elif weather_id == rango:
            return icono
    return "bi-question-circle"  # Icono por defecto


# Debugging
# Print the URL map to see all registered routes
#print(app.url_map)

# Database Connection with Timeout
def get_db_connection():
    conn = sqlite3.connect('mantenimiento_agricola.db', timeout=10)  # Espera hasta 10 segundos
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    app.run(debug=True, threaded=False)