from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth.models import authenticate_user, update_last_login, create_user
from auth.decorators import admin_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = authenticate_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            update_last_login(user['id'])
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Customs Officer')
        
        if create_user(name, email, password, role):
            flash('User created successfully!', 'success')
            return redirect(url_for('auth.register'))
        else:
            flash('Email already registered.', 'danger')
            
    return render_template('register.html')
