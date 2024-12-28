from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

def get_time_difference(start_time, stop_time):
    """
    Calculate the difference between two datetime objects.
    
    Args:
    start_time (datetime): The start time.
    stop_time (datetime): The stop time.
    
    Returns:
    dict: A dictionary containing the difference in days, hours, minutes, and seconds.
    """
    time_difference = stop_time - start_time
    days = time_difference.days
    seconds = time_difference.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    return {
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds
    }

# Example usage:
start_time = datetime(2023, 10, 1, 12, 0, 0)
stop_time = datetime(2023, 10, 2, 14, 30, 45)
time_diff = get_time_difference(start_time, stop_time)
print(time_diff)

class Database:
    def __init__(self, app):
        self.mongo = PyMongo(app)
        self.users = self.mongo.db.users

    def insert_user(self, username, password):
        hashed_password = generate_password_hash(password)
        user_id = self.users.insert_one({'username': username, 'password': hashed_password}).inserted_id
        return user_id

    def find_user(self, username):
        return self.users.find_one({'username': username})

    def check_user_password(self, username, password):
        user = self.find_user(username)
        if user and check_password_hash(user['password'], password):
            return True
        return False

    def update_user(self, username, new_username=None, new_password=None):
        update_fields = {}
        if new_username:
            update_fields['username'] = new_username
        if new_password:
            update_fields['password'] = generate_password_hash(new_password)
        if update_fields:
            self.users.update_one({'username': username}, {'$set': update_fields})


    

    
    def get_time_difference(self, start_time_str, stop_time_str):
        """
        Calculate the difference between two datetime strings.
        
        Args:
        start_time_str (str): The start time as a string.
        stop_time_str (str): The stop time as a string.
        
        Returns:
        dict: A dictionary containing the difference in days, hours, minutes, and seconds.
        """
        # Parse the datetime strings into datetime objects
        start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S.%f')
        stop_time = datetime.strptime(stop_time_str, '%Y-%m-%dT%H:%M:%S.%f')
        
        # Calculate the time difference
        time_difference = stop_time - start_time
        days = time_difference.days
        seconds = time_difference.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds
        }

    def calculate_amount(self, start_time_str, stop_time_str):
        """
        Calculate the amount based on the time difference.
        
        Args:
        start_time_str (str): The start time as a string.
        stop_time_str (str): The stop time as a string.
        
        Returns:
        int: The calculated amount.
        """
        time_diff = self.get_time_difference(start_time_str, stop_time_str)
        total_minutes = (time_diff['days'] * 1440) + (time_diff['hours'] * 60) + time_diff['minutes']
        amount = total_minutes * 10  # 1 minute = 10 units of currency
        return amount

    def stop_timer(self, username):
        user = self.find_user(username)
        if not user or 'start' not in user['booking_data']:
            return None
        
        start_time_str = user['booking_data']['start']
        stop_time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
        
        # Calculate the amount
        amount = self.calculate_amount(start_time_str, stop_time_str)
        
        # Update the user document to remove the start time
        self.users.update_one({'username': username}, {'$unset': {'start': ""}})
        print(amount)
        return amount

    def add_book_space(self, username, booking_data):
        user = self.find_user(username)
        if user:
            start_time = datetime.now().isoformat()  # Convert datetime to ISO format string
            booking_data['start'] = start_time
            self.users.update_one({'username': username}, {'$set': {'booking_data': booking_data}})
            return True
        else:
            return False
        
    def display_book_space(self, username):
        user = self.find_user(username)
        try:
            return user['booking_data']
        except KeyError:
            return None
