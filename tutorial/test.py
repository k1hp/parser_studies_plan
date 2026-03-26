import pytest

# def test_list_diff():
#     assert [1, 2, 3] == [1, 2, 4]   # покажет diff, что отличается последний элемент

# def test_str_diff():
#     assert "hello\nworld" == "hello\nWorld"  # построчный дифф с подсветкой

# @pytest.mark.parametrize("a,b,expected", [
#     (1, 1, 2),
#     (2, 5, 7),
#     (-1, 1, 0),
# ])
# def test_add(a, b, expected):
#     assert a + b == expected

# @pytest.mark.parametrize("num1", [1, 2, 3])
# @pytest.mark.parametrize("num2", [1, 2, 3])
# def test_service(num1, num2):
#     assert num1 + num2 == num1 + num2

@pytest.fixture
def ab():
    # фикстура готовит данные и возвращает их тестам
    return 2, 3

def test_add(ab):
    a, b = ab
    assert a + b == 5

def test_mul(ab):
    a, b = ab
    assert a * b == 6