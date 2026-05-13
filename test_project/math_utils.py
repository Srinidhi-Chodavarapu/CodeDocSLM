import math
def is_prime(n):
    """Returns whether or not `n` is prime.
    
    @param {number} n - The number to check.
    @return {boolean} Whether or not `n` is prime.
    """
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    
    return True


def fibonacci(n):
    """Returns the first n Fibonacci numbers.
    
    @param {number} n - The number of Fibonacci numbers to generate.
    @return {number[]} An array containing the first n Fibonacci numbers.
    """
    if n <= 0:      
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    
    return fib


class Matrix:
    """A simple matrix class that supports setting and getting values, as well as transposing the matrix.
    """
    def __init__(self, rows, cols):
        """Initialize a new matrix with given number of rows and columns.
        
        @param {int} rows - Number of rows.
        @param {int} cols - Number of columns.
        """
        self.rows = rows
        self.cols = cols
        self.data = [[0 for _ in range(cols)] for _ in range(rows)]
    
    def set_value(self, row, col, value):
        """Set the value at the given position in the matrix.
        
        @param {int} row - The row index.
        @param {int} col - The column index.
        @param {any} value - The new value to set.
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.data[row][col] = value
        else:
            raise IndexError("Matrix indices out of range")
    
    def get_value(self, row, col):
        """Returns the element at the given position in the matrix.
        If the index is out of range, raises an `IndexError`.
        
        @param {int} row - The row index (0-based).
        @param {int} col - The column index (0-based).
        
        @return {any} The element at the given position.
        
        @throws {IndexError} If the index is out of range.
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.data[row][col]
        else:
            raise IndexError("Matrix indices out of range")
    
    def transpose(self):
        """Returns a new matrix that is the transpose of this one.
        """
        transposed = Matrix(self.cols, self.rows)
        for i in range(self.rows):
            for j in range(self.cols):
                transposed.set_value(j, i, self.data[i][j])
        return transposed
