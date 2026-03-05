# Fixture: functions with known cyclomatic complexity values.
# CC = base(1) + decision points.
# Do NOT reorder — tests reference these by name.


def trivial():  # CC = 1
    return 42


def single_if(x):  # CC = 2 (1 If)
    if x > 0:
        return x
    return 0


def if_elif(x):  # CC = 3 (If + nested If from elif)
    if x > 0:
        return 1
    elif x < 0:
        return -1
    return 0


def for_loop(items):  # CC = 2 (1 For)
    for item in items:
        print(item)


def while_loop(n):  # CC = 2 (1 While)
    while n > 0:
        n -= 1


def try_except(x):  # CC = 2 (1 ExceptHandler)
    try:
        return 1 / x
    except ZeroDivisionError:
        return 0


def two_excepts(x):  # CC = 3 (2 ExceptHandlers)
    try:
        return 1 / x
    except ZeroDivisionError:
        return 0
    except ValueError:
        return -1


def with_stmt(path):  # CC = 2 (1 With)
    with open(path) as f:
        return f.read()


def assert_stmt(x):  # CC = 2 (1 Assert)
    assert x > 0, "must be positive"
    return x


def bool_and(x, y):  # CC = 2 (BoolOp And with 2 values → +1)
    return x > 0 and y > 0


def bool_or(x, y):  # CC = 2 (BoolOp Or with 2 values → +1)
    return x > 0 or y > 0


def bool_three_and(x, y, z):  # CC = 3 (BoolOp And with 3 values → +2)
    return x > 0 and y > 0 and z > 0


def list_comp_with_if(items):  # CC = 2 (1 comprehension if)
    return [x for x in items if x > 0]


def list_comp_two_ifs(items):  # CC = 3 (2 comprehension ifs in one generator)
    return [x for x in items if x > 0 if x < 100]


def nested_func_isolation(x):  # CC = 2 (only the outer If counts; inner function excluded)
    if x > 0:
        def _inner(y):  # this function's complexity is separate
            if y > 0:
                if y > 10:
                    return y
            return 0
        return _inner(x)
    return 0


def complex_func(x, items):  # CC = 1 + 1(if) + 1(for) + 1(if inside for) + 1(while) = 5
    if x > 0:
        for item in items:
            if item > x:
                print(item)
    while x > 0:
        x -= 1
