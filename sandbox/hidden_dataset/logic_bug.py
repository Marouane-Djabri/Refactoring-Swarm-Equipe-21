"""
A module for performing countdown operations.

This module provides functionality to count down from a given number to 1,
printing each number in the sequence.
"""

def count_down(n):
    """
    Count down from a given number to 1, printing each number in sequence.

    This function takes a positive integer and prints each number starting from
    the given value down to 1, with each number on a new line. The countdown
    stops when the number reaches 0.

    Args:
        n (int): The starting number for the countdown. Must be a positive integer.

    Returns:
        None: This function does not return any value; it only prints the countdown.
    """
    while n > 0:
        print(n)
        n -= 1