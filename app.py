from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone, timedelta
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='templates')

# Database configuration
"""DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)"""

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or f'sqlite:///student_info.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

db = SQLAlchemy(app)

# Models
class Class(db.Model):
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    students = db.relationship('Student', backref='class_ref', lazy=True)

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    email = db.Column(db.String(150))
    address = db.Column(db.Text)
    parent_name = db.Column(db.String(200), nullable=False)
    parent_relationship = db.Column(db.String(50))
    parent_phone = db.Column(db.String(20), nullable=False)
    parent_email = db.Column(db.String(150))
    parent_occupation = db.Column(db.String(100))
    medical_info = db.Column(db.Text)
    previous_school = db.Column(db.String(200))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

# Create tables if they don't exist
with app.app_context():
    db.create_all()
    
    # Add default classes if none exist
    """if Class.query.count() == 0:
        classes = [
            ('EARLY YEARS', 'preschool'),
            ('RECEPTION', 'preschool'),
            ('NURSERY 1', 'preschool'),
            ('NURSERY 2', 'preschool'),
            ('YEAR 1', 'primary'),
            ('YEAR 2', 'primary'),
            ('YEAR 3', 'primary'),
            ('YEAR 4', 'primary'),
            ('YEAR 5', 'primary'),
            ('YEAR 6', 'primary'),
            ('YEAR 7', 'secondary'),
            ('YEAR 8', 'secondary'),
            ('YEAR 9', 'secondary'),
            ('YEAR 10', 'secondary'),
            ('YEAR 11', 'secondary'),
            ('YEAR 12', 'secondary')
        ]
        
        for class_name, level in classes:
            if not Class.query.filter_by(name=class_name).first():
                class_obj = Class(name=class_name, level=level)
                db.session.add(class_obj)
        
        db.session.commit()
        print("Database tables created and classes populated")"""

# Routes
@app.route('/')
def index():
    classes = Class.query.order_by(Class.name).all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', classes=classes, today=today)

@app.route('/api/students', methods=['POST'])
def create_student():
    """Create a new student"""
    try:
        data = request.json
        
        # Validation
        required_fields = ['first_name', 'last_name', 'dob', 
                          'gender', 'class_id', 'parent_name', 'parent_phone']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Generate email: firstname.lastname@arndaleacademy.com
        first_name = data['first_name'].lower().strip()
        last_name = data['last_name'].lower().strip()
        base_email = f"{first_name}.{last_name}@arndaleacademy.com"
        
        # Check if email already exists, add number if it does
        counter = 1
        email = base_email
        while Student.query.filter_by(email=email).first():
            email = f"{first_name}.{last_name}{counter}@arndaleacademy.com"
            counter += 1
        
        # Parse dates
        try:
            dob = datetime.strptime(data['dob'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        
        # Create student object
        student = Student(
            first_name=data['first_name'],
            last_name=data['last_name'],
            middle_name=data.get('middle_name'),
            dob=dob,
            gender=data['gender'],
            class_id=int(data['class_id']),
            email=email,
            address=data.get('address'),
            parent_name=data['parent_name'],
            parent_relationship=data.get('parent_relationship'),
            parent_phone=data['parent_phone'],
            parent_email=data.get('parent_email'),
            parent_occupation=data.get('parent_occupation'),
            medical_info=data.get('medical_info'),
            previous_school=data.get('previous_school'),
            remarks=data.get('remarks')
        )
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Student registered successfully',
            'student_id': str(student.id),
            'email': email,
            'data': {
                'name': f"{student.first_name} {student.last_name}",
                'class': student.class_ref.name if student.class_ref else 'N/A'
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating student: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating student: {str(e)}'
        }), 500

@app.route('/fetch-students/<int:class_id>', methods=['GET'])
def get_students_by_class(class_id):
    """Fetch all students for a given class ID"""
    try:
        # Query students filtered by class_id
        # Using options(joinedload()) can be more efficient if you also need class data,
        # but for a simple list of students, a standard filter is fine.
        students = Student.query.filter_by(class_id=class_id).all()

        if not students:
            return jsonify({
                'success': True,
                'message': 'No students found for this class',
                'students': []
            }), 200

        # Format the student data for the JSON response
        students_list = []
        for student in students:
            students_list.append({
                'id': str(student.id),
                'first_name': student.first_name,
                'last_name': student.last_name,
                'middle_name': student.middle_name,
                'full_name': f"{student.first_name} {student.last_name}".strip(),
                'dob': student.dob.isoformat() if student.dob else None,
                'gender': student.gender,
                'email': student.email,
                'address': student.address,
                'parent_name': student.parent_name,
                'parent_relationship': student.parent_relationship,
                'parent_phone': student.parent_phone,
                'parent_email': student.parent_email,
                'medical_info': student.medical_info,
                'previous_school': student.previous_school,
                'remarks': student.remarks,
                'created_at': student.created_at.isoformat() if student.created_at else None,
                'updated_at': student.updated_at.isoformat() if student.updated_at else None
            })

        return jsonify({
            'success': True,
            'class_id': class_id,
            'student_count': len(students_list),
            'students': students_list
        }), 200

    except Exception as e:
        print(f"Error fetching students for class {class_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500
    
@app.route('/health')
def health_check():
    """Health check endpoint for Vercel"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/init-db', methods=['POST'])
def init_db():
    """Initialize database endpoint"""
    try:
        # Check for secret key
        if request.headers.get('X-Init-Key') != os.environ.get('INIT_KEY'):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        db.create_all()
        
        # Add classes
        classes = [
            ('EARLY YEARS', 'preschool'),
            ('RECEPTION', 'preschool'),
            ('NURSERY 1', 'preschool'),
            ('NURSERY 2', 'preschool'),
            ('YEAR 1', 'primary'),
            ('YEAR 2', 'primary'),
            ('YEAR 3', 'primary'),
            ('YEAR 4', 'primary'),
            ('YEAR 5', 'primary'),
            ('YEAR 6', 'primary'),
            ('YEAR 7', 'secondary'),
            ('YEAR 8', 'secondary'),
            ('YEAR 9', 'secondary'),
            ('YEAR 10', 'secondary'),
            ('YEAR 11', 'secondary'),
            ('YEAR 12', 'secondary')
        ]
        
        for class_name, level in classes:
            if not Class.query.filter_by(name=class_name).first():
                class_obj = Class(name=class_name, level=level)
                db.session.add(class_obj)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Database initialized successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error initializing database: {str(e)}'
        }), 500

# Vercel requires this
@app.route('/favicon.ico')
def favicon():
    return '', 204

# This is required for Vercel
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)