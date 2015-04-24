from functools import wraps

def load_plans(filename):
    pass

def unroll(t):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return t(func(*args, **kwargs))
        return wrapper
    return decorator

class FakePlan:
    def service_list(self):
        return [
            ('Primary Care Physician', 'pcp'),
            ('Emergency Room', 'er')
        ]

class FakePlan2:
    def service_list(self):
        return [
            ('Primary Care Physician', 'pcp'),
            ('Emergency Room', 'er')
        ]

fake_plan = FakePlan()
fake_plan_2 = FakePlan2()

@unroll(set)
def get_service_list():
    yield from fake_plan.service_list()
    yield from FakePlan2.service_list()
