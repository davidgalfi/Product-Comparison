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

@app.route('/analysis/<int:analysis_id>/objects/new')
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5007)
