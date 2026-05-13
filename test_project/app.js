/**
 * Fetches user data from the API.
 * @param {string} userId - The ID of the user to fetch.
 * @returns {Promise<Object|null>} A promise that resolves to the fetched user data or null if an error occurs.
 */
function fetchUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => response.json())
        .catch(error => {
            console.error('Error fetching user:', error);
            return null;
        });
}
/**
 * Validate that the password meets the requirements.
 * @param {string} password - The password to validate.
 * @returns {boolean} True if the password is valid, false otherwise.
 */
const validatePassword = (password) => {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    
    return password.length >= minLength && hasUpperCase && hasLowerCase && hasNumber;
};

/**

 * A simple in-memory list of todos.

 */

class TodoList {
    constructor() {
        this.todos = [];
        this.nextId = 1;
    }
    
    addTodo(title, description) {
        const todo = {
            id: this.nextId++,
            title,
            description,
            completed: false,
            createdAt: new Date()
        };
        this.todos.push(todo);
        return todo;
    }
    
    completeTodo(id) {
        const todo = this.todos.find(t => t.id === id);
        if (todo) {
            todo.completed = true;
            return true;
        }
        return false;
    }
    
    deleteTodo(id) {
        const index = this.todos.findIndex(t => t.id === id);
        if (index !== -1) {
            this.todos.splice(index, 1);
            return true;
        }
        return false;
    }
}

export { fetchUserData, validatePassword, TodoList };
