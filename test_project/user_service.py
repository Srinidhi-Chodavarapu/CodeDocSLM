import json
from datetime import datetime


class UserManager:
    """UserManager class to manage users in a database.
    
    Attributes:
    - database_path (str): Path to the database file.
    - users (list): List of users stored in the database.
    
    Methods:
    - __init__(self, database_path): Constructor method to initialize the UserManager object.
    - add_user(self, username, email, age): Method to add a new user to the database.
    - find_user(self, username): Method to find a user by their username.
    - save_to_file(self): Method to save the current state of the database to a file.
    """

    def __init__(self, database_path):
        """Initialize the database with the given path.
        
        @param {string} database_path The path to the database file.
        """
        self.database_path = database_path
        self.users = []
    
    def add_user(self, username, email, age):
        """Add a new user to the database.
        
        Parameters:
        - username (str): The username of the user.
        - email (str): The email address of the user.
        - age (int): The age of the user.
        
        Returns:
        - dict: The newly created user.
        """
        user = {
            'username': username,
            'email': email,
            'age': age,
            'created_at': datetime.now().isoformat()
        }
        self.users.append(user)
        return user
    
    def find_user(self, username):
        """Find a user by their username.
        
                :param str username: The username to search for.
                :return: The user object if found, otherwise `None`.
        """
        for user in self.users:
            if user['username'] == username:
                return user
        return None
    
    def save_to_file(self):
        """Saves the database to a file in JSON format.
        """
        with open(self.database_path, 'w') as f:
            json.dump(self.users, f, indent=2)


def calculate_average(numbers):
    """Calculate the average of a list of numbers.
    
    @param {number[]} numbers - The list of numbers to calculate the average of.
    @return {number} The average of the numbers in the list.
    """
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)


def filter_adults(users):
    return [user for user in users if user.get('age', 0) >= 18]
