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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
