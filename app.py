from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3
import json
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

# Database configuration
DATABASE = 'product_comparisons.db'

def get_db_connection():
    """Get database connection with row factory for dict-like access"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    
    # Analysis table - stores comparison groups
    conn.execute('''
        CREATE TABLE IF NOT EXISTS analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Fields table - stores custom fields for each analysis
    conn.execute('''
        CREATE TABLE IF NOT EXISTS fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            field_type TEXT NOT NULL DEFAULT 'text',
            field_unit TEXT,
            is_required BOOLEAN DEFAULT 0,
            display_order INTEGER DEFAULT 0,
            FOREIGN KEY (analysis_id) REFERENCES analysis (id) ON DELETE CASCADE
        )
    ''')
    
    # Objects table - stores items being compared
    conn.execute('''
        CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            object_name TEXT NOT NULL,
            brand TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (analysis_id) REFERENCES analysis (id) ON DELETE CASCADE
        )
    ''')
    
    # Object values table - stores field values for each object
    conn.execute('''
        CREATE TABLE IF NOT EXISTS object_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER NOT NULL,
            field_id INTEGER NOT NULL,
            field_value TEXT,
            FOREIGN KEY (object_id) REFERENCES objects (id) ON DELETE CASCADE,
            FOREIGN KEY (field_id) REFERENCES fields (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Field type options for dynamic forms
FIELD_TYPES = {
    'text': 'Text',
    'number': 'Number',
    'decimal': 'Decimal',
    'boolean': 'Yes/No',
    'select': 'Dropdown',
    'rating': 'Rating (1-5)',
    'price': 'Price',
    'date': 'Date'
}

@app.route('/')
def dashboard():
    """Dashboard view with overview of all comparisons"""
    conn = get_db_connection()
    
    # Get recent analyses
    recent_analyses = conn.execute('''
        SELECT a.*, COUNT(o.id) as object_count
        FROM analysis a
        LEFT JOIN objects o ON a.id = o.analysis_id
        GROUP BY a.id
        ORDER BY a.created_at DESC
        LIMIT 6
    ''').fetchall()
    
    # Get statistics
    total_analyses = conn.execute('SELECT COUNT(*) FROM analysis').fetchone()[0]
    total_objects = conn.execute('SELECT COUNT(*) FROM objects').fetchone()[0]
    
    # Category distribution
    categories = conn.execute('''
        SELECT category, COUNT(*) as count
        FROM analysis
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('dashboard.html',
                         recent_analyses=recent_analyses,
                         total_analyses=total_analyses,
                         total_objects=total_objects,
                         categories=categories)

# app.py - Add these routes after the dashboard route

@app.route('/create-analysis', methods=['POST'])
def create_analysis():
    """Create a new analysis"""
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Analysis name is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.execute('''
            INSERT INTO analysis (name, description, category)
            VALUES (?, ?, ?)
        ''', (name, description, category))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'analysis_id': analysis_id,
            'message': 'Analysis created successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analysis/<int:analysis_id>/setup')
def analysis_setup(analysis_id):
    """Setup page for defining custom fields"""
    conn = get_db_connection()
    
    # Get analysis details
    analysis = conn.execute(
        'SELECT * FROM analysis WHERE id = ?', (analysis_id,)
    ).fetchone()
    
    if not analysis:
        flash('Analysis not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get existing fields
    fields = conn.execute('''
        SELECT * FROM fields 
        WHERE analysis_id = ? 
        ORDER BY display_order ASC
    ''', (analysis_id,)).fetchall()
    
    conn.close()
    
    return render_template('analysis_setup.html', 
                         analysis=analysis, 
                         fields=fields,
                         field_types=FIELD_TYPES)

@app.route('/analysis/<int:analysis_id>/fields', methods=['POST'])
def add_field(analysis_id):
    """Add a custom field to analysis"""
    try:
        data = request.get_json()
        
        field_name = data.get('field_name', '').strip()
        field_type = data.get('field_type', 'text')
        field_unit = data.get('field_unit', '').strip()
        is_required = data.get('is_required', False)
        
        if not field_name:
            return jsonify({'success': False, 'error': 'Field name is required'}), 400
        
        if field_type not in FIELD_TYPES:
            return jsonify({'success': False, 'error': 'Invalid field type'}), 400
        
        conn = get_db_connection()
        
        # Get next display order
        max_order = conn.execute(
            'SELECT COALESCE(MAX(display_order), 0) FROM fields WHERE analysis_id = ?',
            (analysis_id,)
        ).fetchone()[0]
        
        # Insert new field
        cursor = conn.execute('''
            INSERT INTO fields (analysis_id, field_name, field_type, field_unit, is_required, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (analysis_id, field_name, field_type, field_unit, is_required, max_order + 1))
        
        field_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'field_id': field_id,
            'message': 'Field added successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analysis/<int:analysis_id>/fields/<int:field_id>', methods=['DELETE'])
def delete_field(analysis_id, field_id):
    """Delete a custom field"""
    try:
        conn = get_db_connection()
        
        # Delete field and its values
        conn.execute('DELETE FROM object_values WHERE field_id = ?', (field_id,))
        conn.execute('DELETE FROM fields WHERE id = ? AND analysis_id = ?', (field_id, analysis_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Field deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analysis/<int:analysis_id>/fields/reorder', methods=['POST'])
def reorder_fields(analysis_id):
    """Reorder fields"""
    try:
        field_ids = request.get_json().get('field_ids', [])
        
        conn = get_db_connection()
        
        for index, field_id in enumerate(field_ids):
            conn.execute(
                'UPDATE fields SET display_order = ? WHERE id = ? AND analysis_id = ?',
                (index, field_id, analysis_id)
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Fields reordered successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analysis/<int:analysis_id>')
def view_analysis(analysis_id):
    """View analysis with objects and comparison table"""
    conn = get_db_connection()
    
    # Get analysis details
    analysis = conn.execute(
        'SELECT * FROM analysis WHERE id = ?', (analysis_id,)
    ).fetchone()
    
    if not analysis:
        flash('Analysis not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get fields
    fields = conn.execute('''
        SELECT * FROM fields 
        WHERE analysis_id = ? 
        ORDER BY display_order ASC
    ''', (analysis_id,)).fetchall()
    
    # Get objects with their values
    objects = conn.execute('''
        SELECT * FROM objects 
        WHERE analysis_id = ? 
        ORDER BY created_at DESC
    ''', (analysis_id,)).fetchall()
    
    # Get all field values for objects
    object_values = {}
    for obj in objects:
        values = conn.execute('''
            SELECT f.id as field_id, f.field_name, ov.field_value
            FROM fields f
            LEFT JOIN object_values ov ON f.id = ov.field_id AND ov.object_id = ?
            WHERE f.analysis_id = ?
            ORDER BY f.display_order ASC
        ''', (obj['id'], analysis_id)).fetchall()
        
        object_values[obj['id']] = {v['field_id']: v['field_value'] for v in values}
    
    conn.close()
    
    return render_template('analysis_view.html',
                         analysis=analysis,
                         fields=fields,
                         objects=objects,
                         object_values=object_values)

@app.route('/analysis/<int:analysis_id>/objects/new', methods=['GET', 'POST'])
def new_object(analysis_id):
    """Form to add new object to analysis"""
    conn = get_db_connection()
    
    # Get analysis details
    analysis = conn.execute(
        'SELECT * FROM analysis WHERE id = ?', (analysis_id,)
    ).fetchone()
    
    if not analysis:
        flash('Analysis not found!', 'error')
        return redirect(url_for('dashboard'))
    
    # Get fields
    fields = conn.execute('''
        SELECT * FROM fields 
        WHERE analysis_id = ? 
        ORDER BY display_order ASC
    ''', (analysis_id,)).fetchall()
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        try:
            object_name = request.form.get('object_name', '').strip()
            brand = request.form.get('brand', '').strip()
            image_url = request.form.get('image_url', '').strip()
            
            if not object_name:
                flash('Object name is required!', 'error')
                conn.close()
                return render_template('object_form.html',
                                     analysis=analysis,
                                     fields=fields,
                                     mode='create')
            
            # Create object
            cursor = conn.execute('''
                INSERT INTO objects (analysis_id, object_name, brand, image_url)
                VALUES (?, ?, ?, ?)
            ''', (analysis_id, object_name, brand, image_url))
            
            object_id = cursor.lastrowid
            
            # Save field values
            for field in fields:
                field_value = request.form.get(f'field_{field["id"]}', '').strip()
                
                if field_value or field['is_required']:
                    conn.execute('''
                        INSERT INTO object_values (object_id, field_id, field_value)
                        VALUES (?, ?, ?)
                    ''', (object_id, field['id'], field_value))
            
            conn.commit()
            conn.close()
            
            flash(f'Object "{object_name}" added successfully!', 'success')
            return redirect(url_for('view_analysis', analysis_id=analysis_id))
            
        except Exception as e:
            conn.close()
            flash(f'Error creating object: {str(e)}', 'error')
            return render_template('object_form.html',
                                 analysis=analysis,
                                 fields=fields,
                                 mode='create')
    
    # Handle GET request (show form)
    conn.close()
    return render_template('object_form.html',
                         analysis=analysis,
                         fields=fields,
                         mode='create')

@app.route('/analysis/<int:analysis_id>/objects', methods=['POST'])
def create_object(analysis_id):
    """Create new object in analysis"""
    try:
        object_name = request.form.get('object_name', '').strip()
        brand = request.form.get('brand', '').strip()
        image_url = request.form.get('image_url', '').strip()
        
        if not object_name:
            flash('Object name is required!', 'error')
            return redirect(url_for('new_object', analysis_id=analysis_id))
        
        conn = get_db_connection()
        
        # Create object
        cursor = conn.execute('''
            INSERT INTO objects (analysis_id, object_name, brand, image_url)
            VALUES (?, ?, ?, ?)
        ''', (analysis_id, object_name, brand, image_url))
        
        object_id = cursor.lastrowid
        
        # Get fields for this analysis
        fields = conn.execute(
            'SELECT * FROM fields WHERE analysis_id = ?', (analysis_id,)
        ).fetchall()
        
        # Save field values
        for field in fields:
            field_value = request.form.get(f'field_{field["id"]}', '').strip()
            
            if field_value or field['is_required']:
                conn.execute('''
                    INSERT INTO object_values (object_id, field_id, field_value)
                    VALUES (?, ?, ?)
                ''', (object_id, field['id'], field_value))
        
        conn.commit()
        conn.close()
        
        flash(f'Object "{object_name}" added successfully!', 'success')
        return redirect(url_for('view_analysis', analysis_id=analysis_id))
        
    except Exception as e:
        flash(f'Error creating object: {str(e)}', 'error')
        return redirect(url_for('new_object', analysis_id=analysis_id))


# app.py - Add these advanced routes and features

@app.route('/analysis/<int:analysis_id>/objects/<int:object_id>/edit', methods=['GET', 'POST'])
def edit_object(analysis_id, object_id):
    """Edit object form and processing"""
    conn = get_db_connection()
    
    # Get analysis and object details
    analysis = conn.execute(
        'SELECT * FROM analysis WHERE id = ?', (analysis_id,)
    ).fetchone()
    
    if not analysis:
        flash('Analysis not found!', 'error')
        return redirect(url_for('dashboard'))
    
    object_data = conn.execute(
        'SELECT * FROM objects WHERE id = ? AND analysis_id = ?', 
        (object_id, analysis_id)
    ).fetchone()
    
    if not object_data:
        flash('Object not found!', 'error')
        return redirect(url_for('view_analysis', analysis_id=analysis_id))
    
    # Get fields and values
    fields = conn.execute('''
        SELECT * FROM fields 
        WHERE analysis_id = ? 
        ORDER BY display_order ASC
    ''', (analysis_id,)).fetchall()
    
    object_values = {}
    if request.method == 'GET':
        values = conn.execute('''
            SELECT field_id, field_value 
            FROM object_values 
            WHERE object_id = ?
        ''', (object_id,)).fetchall()
        
        for value in values:
            object_values[value['field_id']] = value['field_value']
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        try:
            object_name = request.form.get('object_name', '').strip()
            brand = request.form.get('brand', '').strip()
            image_url = request.form.get('image_url', '').strip()
            
            if not object_name:
                flash('Object name is required!', 'error')
                conn.close()
                return render_template('object_form.html',
                                     analysis=analysis,
                                     fields=fields,
                                     object=object_data,
                                     object_values=object_values,
                                     mode='edit')
            
            # Update object
            conn.execute('''
                UPDATE objects 
                SET object_name = ?, brand = ?, image_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND analysis_id = ?
            ''', (object_name, brand, image_url, object_id, analysis_id))
            
            # Delete and recreate field values
            conn.execute('DELETE FROM object_values WHERE object_id = ?', (object_id,))
            
            for field in fields:
                field_value = request.form.get(f'field_{field["id"]}', '').strip()
                if field_value:
                    conn.execute('''
                        INSERT INTO object_values (object_id, field_id, field_value)
                        VALUES (?, ?, ?)
                    ''', (object_id, field['id'], field_value))
            
            conn.commit()
            conn.close()
            
            flash(f'Object "{object_name}" updated successfully!', 'success')
            return redirect(url_for('view_analysis', analysis_id=analysis_id))
            
        except Exception as e:
            conn.close()
            flash(f'Error updating object: {str(e)}', 'error')
    
    conn.close()
    return render_template('object_form.html',
                         analysis=analysis,
                         fields=fields,
                         object=object_data,
                         object_values=object_values,
                         mode='edit')


@app.route('/analysis/<int:analysis_id>/objects/<int:object_id>', methods=['POST'])
def update_object(analysis_id, object_id):
    """Update existing object"""
    try:
        object_name = request.form.get('object_name', '').strip()
        brand = request.form.get('brand', '').strip()
        image_url = request.form.get('image_url', '').strip()
        
        if not object_name:
            flash('Object name is required!', 'error')
            return redirect(url_for('edit_object', analysis_id=analysis_id, object_id=object_id))
        
        conn = get_db_connection()
        
        # Update object
        conn.execute('''
            UPDATE objects 
            SET object_name = ?, brand = ?, image_url = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND analysis_id = ?
        ''', (object_name, brand, image_url, object_id, analysis_id))
        
        # Delete existing field values
        conn.execute('DELETE FROM object_values WHERE object_id = ?', (object_id,))
        
        # Get fields for this analysis
        fields = conn.execute(
            'SELECT * FROM fields WHERE analysis_id = ?', (analysis_id,)
        ).fetchall()
        
        # Save new field values
        for field in fields:
            field_value = request.form.get(f'field_{field["id"]}', '').strip()
            
            if field_value:
                conn.execute('''
                    INSERT INTO object_values (object_id, field_id, field_value)
                    VALUES (?, ?, ?)
                ''', (object_id, field['id'], field_value))
        
        conn.commit()
        conn.close()
        
        flash(f'Object "{object_name}" updated successfully!', 'success')
        return redirect(url_for('view_analysis', analysis_id=analysis_id))
        
    except Exception as e:
        flash(f'Error updating object: {str(e)}', 'error')
        return redirect(url_for('edit_object', analysis_id=analysis_id, object_id=object_id))

@app.route('/analysis/<int:analysis_id>/objects/<int:object_id>', methods=['DELETE'])
def delete_object(analysis_id, object_id):
    """Delete object"""
    try:
        conn = get_db_connection()
        
        # Get object name for confirmation
        object_data = conn.execute(
            'SELECT object_name FROM objects WHERE id = ? AND analysis_id = ?',
            (object_id, analysis_id)
        ).fetchone()
        
        if not object_data:
            return jsonify({'success': False, 'error': 'Object not found'}), 404
        
        # Delete object values first (foreign key constraint)
        conn.execute('DELETE FROM object_values WHERE object_id = ?', (object_id,))
        
        # Delete object
        conn.execute('DELETE FROM objects WHERE id = ? AND analysis_id = ?', 
                    (object_id, analysis_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Object "{object_data["object_name"]}" deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analysis/<int:analysis_id>/export')
def export_analysis(analysis_id):
    """Export analysis data in multiple formats"""
    format_type = request.args.get('format', 'csv')
    
    conn = get_db_connection()
    
    # Get analysis details
    analysis = conn.execute(
        'SELECT * FROM analysis WHERE id = ?', (analysis_id,)
    ).fetchone()
    
    if not analysis:
        return jsonify({'error': 'Analysis not found'}), 404
    
    # Get fields and objects
    fields = conn.execute('''
        SELECT * FROM fields 
        WHERE analysis_id = ? 
        ORDER BY display_order ASC
    ''', (analysis_id,)).fetchall()
    
    objects = conn.execute('''
        SELECT o.*, GROUP_CONCAT(f.field_name || ':' || ov.field_value, '|') as values
        FROM objects o
        LEFT JOIN object_values ov ON o.id = ov.object_id
        LEFT JOIN fields f ON ov.field_id = f.id
        WHERE o.analysis_id = ?
        GROUP BY o.id
        ORDER BY o.created_at DESC
    ''', (analysis_id,)).fetchall()
    
    conn.close()
    
    if format_type == 'json':
        return export_to_json(analysis, fields, objects)
    elif format_type == 'csv':
        return export_to_csv(analysis, fields, objects)
    else:
        return jsonify({'error': 'Unsupported format'}), 400

def export_to_csv(analysis, fields, objects):
    """Export analysis to CSV format"""
    import csv
    import io
    from flask import make_response
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    header = ['Object Name', 'Brand', 'Image URL', 'Created Date']
    header.extend([field['field_name'] for field in fields])
    writer.writerow(header)
    
    # Write data rows
    for obj in objects:
        row = [obj['object_name'], obj['brand'] or '', obj['image_url'] or '', obj['created_at']]
        
        # Parse field values
        values_dict = {}
        if obj['values']:
            for value_pair in obj['values'].split('|'):
                if ':' in value_pair:
                    field_name, field_value = value_pair.split(':', 1)
                    values_dict[field_name] = field_value
        
        # Add field values in correct order
        for field in fields:
            row.append(values_dict.get(field['field_name'], ''))
        
        writer.writerow(row)
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{analysis["name"]}_comparison.csv"'
    
    return response

def export_to_json(analysis, fields, objects):
    """Export analysis to JSON format"""
    from flask import jsonify
    
    # Build structured data
    export_data = {
        'analysis': {
            'id': analysis['id'],
            'name': analysis['name'],
            'description': analysis['description'],
            'category': analysis['category'],
            'created_at': analysis['created_at'],
            'updated_at': analysis['updated_at']
        },
        'fields': [
            {
                'id': field['id'],
                'name': field['field_name'],
                'type': field['field_type'],
                'unit': field['field_unit'],
                'required': bool(field['is_required']),
                'order': field['display_order']
            }
            for field in fields
        ],
        'objects': []
    }
    
    # Add objects data
    for obj in objects:
        obj_data = {
            'id': obj['id'],
            'name': obj['object_name'],
            'brand': obj['brand'],
            'image_url': obj['image_url'],
            'created_at': obj['created_at'],
            'field_values': {}
        }
        
        # Parse field values
        if obj['values']:
            for value_pair in obj['values'].split('|'):
                if ':' in value_pair:
                    field_name, field_value = value_pair.split(':', 1)
                    obj_data['field_values'][field_name] = field_value
        
        export_data['objects'].append(obj_data)
    
    response = jsonify(export_data)
    response.headers['Content-Disposition'] = f'attachment; filename="{analysis["name"]}_comparison.json"'
    
    return response

@app.route('/search')
def search():
    """Global search across all analyses"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'results': []})
    
    conn = get_db_connection()
    
    # Search analyses
    analyses = conn.execute('''
        SELECT id, name, description, category, created_at
        FROM analysis 
        WHERE name LIKE ? OR description LIKE ? OR category LIKE ?
        ORDER BY updated_at DESC
        LIMIT 10
    ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    
    # Search objects
    objects = conn.execute('''
        SELECT o.id, o.object_name, o.brand, a.id as analysis_id, a.name as analysis_name
        FROM objects o
        JOIN analysis a ON o.analysis_id = a.id
        WHERE o.object_name LIKE ? OR o.brand LIKE ?
        ORDER BY o.created_at DESC
        LIMIT 10
    ''', (f'%{query}%', f'%{query}%')).fetchall()
    
    conn.close()
    
    results = {
        'analyses': [dict(analysis) for analysis in analyses],
        'objects': [dict(obj) for obj in objects]
    }
    
    return jsonify(results)

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard with system statistics"""
    conn = get_db_connection()
    
    # Get comprehensive statistics
    stats = {
        'total_analyses': conn.execute('SELECT COUNT(*) FROM analysis').fetchone()[0],
        'total_objects': conn.execute('SELECT COUNT(*) FROM objects').fetchone()[0],
        'total_fields': conn.execute('SELECT COUNT(*) FROM fields').fetchone()[0],
        'recent_activity': conn.execute('''
            SELECT 'analysis' as type, name as title, created_at 
            FROM analysis 
            UNION ALL
            SELECT 'object' as type, object_name as title, created_at 
            FROM objects
            ORDER BY created_at DESC 
            LIMIT 10
        ''').fetchall(),
        'popular_categories': conn.execute('''
            SELECT category, COUNT(*) as count
            FROM analysis
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 5
        ''').fetchall(),
        'field_type_distribution': conn.execute('''
            SELECT field_type, COUNT(*) as count
            FROM fields
            GROUP BY field_type
            ORDER BY count DESC
        ''').fetchall()
    }
    
    conn.close()
    
    return render_template('admin_dashboard.html', stats=stats)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        conn = get_db_connection()
        conn.execute('SELECT 1').fetchone()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500


# app.py - Add these missing routes after your existing routes

@app.route('/analysis/<int:analysis_id>/edit')
def edit_analysis(analysis_id):
    """Edit analysis settings"""
    conn = get_db_connection()
    
    analysis = conn.execute(
        'SELECT * FROM analysis WHERE id = ?', (analysis_id,)
    ).fetchone()
    
    if not analysis:
        flash('Analysis not found!', 'error')
        return redirect(url_for('dashboard'))
    
    conn.close()
    
    return render_template('edit_analysis.html', analysis=analysis)

@app.route('/analysis/<int:analysis_id>/edit', methods=['POST'])
def update_analysis(analysis_id):
    """Update analysis settings"""
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        
        if not name:
            flash('Analysis name is required!', 'error')
            return redirect(url_for('edit_analysis', analysis_id=analysis_id))
        
        conn = get_db_connection()
        conn.execute('''
            UPDATE analysis 
            SET name = ?, description = ?, category = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name, description, category, analysis_id))
        
        conn.commit()
        conn.close()
        
        flash('Analysis updated successfully!', 'success')
        return redirect(url_for('view_analysis', analysis_id=analysis_id))
        
    except Exception as e:
        flash(f'Error updating analysis: {str(e)}', 'error')
        return redirect(url_for('edit_analysis', analysis_id=analysis_id))

@app.route('/analysis/<int:analysis_id>/delete', methods=['DELETE'])
def delete_analysis(analysis_id):
    """Delete analysis and all related data"""
    try:
        conn = get_db_connection()
        
        # Get analysis name for confirmation
        analysis = conn.execute(
            'SELECT name FROM analysis WHERE id = ?', (analysis_id,)
        ).fetchone()
        
        if not analysis:
            return jsonify({'success': False, 'error': 'Analysis not found'}), 404
        
        # Delete in correct order (foreign key constraints)
        # Delete object values first
        conn.execute('''
            DELETE FROM object_values 
            WHERE object_id IN (
                SELECT id FROM objects WHERE analysis_id = ?
            )
        ''', (analysis_id,))
        
        # Delete objects
        conn.execute('DELETE FROM objects WHERE analysis_id = ?', (analysis_id,))
        
        # Delete fields
        conn.execute('DELETE FROM fields WHERE analysis_id = ?', (analysis_id,))
        
        # Delete analysis
        conn.execute('DELETE FROM analysis WHERE id = ?', (analysis_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Analysis "{analysis["name"]}" deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analysis/<int:analysis_id>/share')
def share_analysis(analysis_id):
    """Generate shareable link for analysis"""
    conn = get_db_connection()
    
    analysis = conn.execute(
        'SELECT * FROM analysis WHERE id = ?', (analysis_id,)
    ).fetchone()
    
    if not analysis:
        flash('Analysis not found!', 'error')
        return redirect(url_for('dashboard'))
    
    conn.close()
    
    # Generate shareable data
    share_data = {
        'analysis_id': analysis_id,
        'analysis_name': analysis['name'],
        'share_url': f"{request.host_url}analysis/{analysis_id}",
        'embed_code': f'<iframe src="{request.host_url}analysis/{analysis_id}/embed" width="100%" height="600"></iframe>'
    }
    
    return render_template('share_analysis.html', analysis=analysis, share_data=share_data)

@app.route('/analysis/<int:analysis_id>/duplicate', methods=['POST'])
def duplicate_analysis(analysis_id):
    """Create a copy of an existing analysis"""
    try:
        conn = get_db_connection()
        
        # Get original analysis
        original = conn.execute(
            'SELECT * FROM analysis WHERE id = ?', (analysis_id,)
        ).fetchone()
        
        if not original:
            return jsonify({'success': False, 'error': 'Analysis not found'}), 404
        
        # Create new analysis
        cursor = conn.execute('''
            INSERT INTO analysis (name, description, category)
            VALUES (?, ?, ?)
        ''', (f"{original['name']} (Copy)", original['description'], original['category']))
        
        new_analysis_id = cursor.lastrowid
        
        # Copy fields
        fields = conn.execute(
            'SELECT * FROM fields WHERE analysis_id = ? ORDER BY display_order',
            (analysis_id,)
        ).fetchall()
        
        field_mapping = {}
        for field in fields:
            cursor = conn.execute('''
                INSERT INTO fields (analysis_id, field_name, field_type, field_unit, is_required, display_order)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (new_analysis_id, field['field_name'], field['field_type'], 
                  field['field_unit'], field['is_required'], field['display_order']))
            
            field_mapping[field['id']] = cursor.lastrowid
        
        # Copy objects and their values
        objects = conn.execute(
            'SELECT * FROM objects WHERE analysis_id = ?', (analysis_id,)
        ).fetchall()
        
        for obj in objects:
            cursor = conn.execute('''
                INSERT INTO objects (analysis_id, object_name, brand, image_url)
                VALUES (?, ?, ?, ?)
            ''', (new_analysis_id, obj['object_name'], obj['brand'], obj['image_url']))
            
            new_object_id = cursor.lastrowid
            
            # Copy object values
            values = conn.execute(
                'SELECT * FROM object_values WHERE object_id = ?', (obj['id'],)
            ).fetchall()
            
            for value in values:
                if value['field_id'] in field_mapping:
                    conn.execute('''
                        INSERT INTO object_values (object_id, field_id, field_value)
                        VALUES (?, ?, ?)
                    ''', (new_object_id, field_mapping[value['field_id']], value['field_value']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Analysis duplicated successfully',
            'new_analysis_id': new_analysis_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5007)
