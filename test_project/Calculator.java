/**
 * This class provides methods to perform basic arithmetic operations and check for palindromes.
 * It also includes a method to count the number of vowels in a string.
 *
 * @see #add(int, int)
 * @see #subtract(int, int)
 * @see #divide(double, double)
 * @see #multiply(int, int)
 *
 * @author John Doe
 */
public class Calculator {
    /**
     * Adds two integers together.
     *
     * @param a The first integer.
     * @param b The second integer.
     * @return The sum of a and b.
     */
    public int add(int a, int b) {
        return a + b;
    }
       
/**
       
 * Subtract two integers.
       
 *
       
 * @param a The first integer.
       
 * @param b The second integer.
       
 * @return The result of a-b.
       
 */
       
    public int subtract(int a, int b) {
        return a - b;
    }

/**

 * Divides two numbers.

 *

 * @param a The numerator.

 * @param b The denominator.

 * @return The result of dividing a by b.

 * @throws ArithmeticException If b is zero.

 */

    
    public double divide(double a, double b) throws ArithmeticException {
        if (b == 0) {
            throw new ArithmeticException("Division by zero");
        }
        return a / b;
    }
 
/**
 
 * Multiply two integers.
 
 *
 
 * @param a first integer.
 
 * @param b second integer.
 
 * @return the product of a and b.
 
 */
 
    public int multiply(int a, int b) {
        return a * b;
    }
}
/**
 * Utility class to help with string manipulation.
 *
 * @author <NAME>
 * @version 1.0.0
 */
class StringHelper {
    /**
     * Reverses the given string.
     *
     * @param input The string to be reversed.
     * @return The reversed string.
     */
    public static String reverse(String input) {
        return new StringBuilder(input).reverse().toString();
    }
    
/**
    
 * Returns true if the given string is a palindrome.
    
 *
    
 * @param input The string to check.
    
 * @return True if the string is a palindrome.
    
 */
    
    public static boolean isPalindrome(String input) {
        String cleaned = input.toLowerCase().replaceAll("\\s+", "");
        return cleaned.equals(reverse(cleaned));
    }
    
/**
    
 * Counts the number of vowels in a given string.
    
 *
    
 * @param input The string to count vowels in.
    
 * @return The number of vowels in the string.
    
 */
    
    public static int countVowels(String input) {
        int count = 0;
        String vowels = "aeiouAEIOU";
        
        for (char c : input.toCharArray()) {
            if (vowels.indexOf(c) != -1) {
                count++;
            }
        }
        
        return count;
    }
}
