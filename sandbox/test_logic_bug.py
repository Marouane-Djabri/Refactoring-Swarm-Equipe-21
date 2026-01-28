import pytest

def test_division_happy_path():
    X = 10
    Y = 2
    result = X / Y
    assert result == 5.0

def test_division_by_zero_handling(capsys):
    X = 10
    Y = 0
    if Y != 0:
        print(X / Y)
    else:
        print('Error: Division by zero')
    captured = capsys.readouterr()
    assert captured.out.strip() == 'Error: Division by zero'