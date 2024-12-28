import asyncio
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, jsonify, send_file
import cv2
import threading
import numpy as np
# import flask_pymongo
import requests
from datetime import datetime
import os
from util import get_parking_spots_bboxes, empty_or_not


app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://msnithin84:Nithin@cluster0.wob2cfi.mongodb.net/opencv_db"
app.secret_key = 'your_secret_key'

def data_db():
    from db import Database 
    db = Database(app)
    return db

mask_path = 'mask_1920_1080.png'
video_path = 'parking_1920_1080.mp4'

mask = cv2.imread(mask_path, 0)
cap = cv2.VideoCapture(video_path)

connected_components = cv2.connectedComponentsWithStats(mask, 4, cv2.CV_32S)
spots = get_parking_spots_bboxes(connected_components)

spots_status = [None for j in spots]
diffs = [None for j in spots]

previous_frame = None
frame_nmr = 0
step = 30

global free_spaces, occupied_spaces

free_spaces = 0
occupied_spaces = 0

def calc_diff(im1, im2):
    return np.abs(np.mean(im1) - np.mean(im2))

def generate_frames():
    global previous_frame, frame_nmr
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_nmr % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if previous_frame is not None:
                for spot_indx, spot in enumerate(spots):
                    x1, y1, x2, y2 = spot
                    spot_img = gray[y1:y2, x1:x2]
                    diffs[spot_indx] = calc_diff(spot_img, previous_frame[y1:y2, x1:x2])
                    spots_status[spot_indx] = empty_or_not(diffs[spot_indx])
            previous_frame = gray

        for spot_indx, spot in enumerate(spots):
            x1, y1, x2, y2 = spot
            color = (0, 255, 0) if spots_status[spot_indx] else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        frame_nmr += 1

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

 # Update every 5 seconds

@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html')
    return render_template('login.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/space_count')
def space_count_route():
    free_spaces = session.get('free_space', 0)
    occupied_spaces = session.get('occupied_spaces', 0)
    session['free_spaces'] = free_spaces
    session['occupied_spaces'] = occupied_spaces
    return jsonify({'free': free_spaces, 'occupied': occupied_spaces})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Validate username and password
        db=data_db()
        if db.check_user_password(username, password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Validate input
        if not username or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('register'))

        # Save user information to MongoDB
        db = data_db()
        if db.insert_user(username, password):
            flash('User registered successfully', 'success')
            return redirect(url_for('login'))
        else:
            flash('User already exists', 'error')
            return redirect(url_for('register'))
    else:       
        return render_template('register.html') 

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/booking')
def booking():
    return render_template('booking.html', free_spaces=free_spaces, occupied_spaces=occupied_spaces)

@app.route('/book_space', methods=['GET', 'POST'])
def book_space():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        owner_name = request.form['owner_name']
        vehicle_name = request.form['vehicle_name']
        vehicle_number = request.form['vehicle_number']
        date = request.form['date']
        car_number = request.form['car_number']

        # Validate input
        if not owner_name or not vehicle_name or not vehicle_number or not date or not car_number:
            flash('All fields are required', 'error')
            return redirect(url_for('book_space'))

        # Save booking information to MongoDB
        booking_data = {
            'owner_name': owner_name,
            'vehicle_name': vehicle_name,
            'vehicle_number': vehicle_number,
            'date': date,
            'car_number': car_number
        }
        # try:
        #     response = requests.get('http://http://127.0.0.1:5000/space_count')
        #     response.raise_for_status()  # Raise an exception for HTTP errors
        #     data = response.json()
        #     free_spaces = data.get('free', 0)
        #     occupied_spaces = data.get('occupied', 0)
        # except requests.RequestException as e:
        #     flash('Error fetching space data', 'error')
        #     free_spaces = 0
        #     occupied_spaces = 0
        # free_spaces -= 1
        # occupied_spaces += 1
        db = data_db()
        if db.add_book_space(session['username'], booking_data):
            flash('Booking information updated successfully', 'success')
            return redirect(url_for('booking'))
        else:
            flash('User does not exist', 'error')
            return redirect(url_for('book_space'))
    else:
        return render_template('booking.html')

def display_amount():
    db = data_db()
    username = session['username']
    amount = db.stop_timer(username)
    print( amount)
    if amount is None:
        flash('Error stopping timer. Please try again.', 'error')
        return redirect(url_for('exit_lot'))
 # Remove microseconds
    # Format the time_difference to a simpler format
    return  amount
    

@app.route('/exit_lot', methods=['GET', 'POST'])
def exit_lot():
    if 'username' not in session:
        return redirect(url_for('login'))
    global db
    db = data_db()
    details = db.display_book_space(session['username'])
    if request.method == 'POST': 
        amount = display_amount()
        
        return render_template('exit_lot.html',  amount=amount, details=details)
    
    if details and 'start' in details:
        # Format the start time to a simpler format
        start_time = datetime.strptime(details['start'], '%Y-%m-%dT%H:%M:%S.%f').strftime('%Y-%m-%d %H:%M:%S')
        details['start'] = start_time
        return render_template('exit_lot.html',  amount=None, details=details)
    else:
        flash('No active booking found', 'error')
        return render_template('exit_lot.html',  amount=None, details=None)

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    db = data_db()
    user = db.find_user(username)
    return render_template('profile.html', user=user)

@app.route('/payment')  
def payment():
    return render_template('payment.html')
 

if __name__ == '__main__':
    app.run(debug=True)