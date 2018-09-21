import pytest


@pytest.fixture(scope="function")
def post_budget():
    return {
        'type': "post",
        'owner': 'test.test1',
        'json_metadata': "{}",
        'balance': "1.000000000 SCR",
        'start': "1970-01-01T00:00:00",
        'deadline': "1970-01-01T00:00:30"
    }


@pytest.fixture(scope="function")
def banner_budget():
    return {
        'type': "banner",
        'owner': 'test.test1',
        'json_metadata': "{}",
        'balance': "1.000000000 SCR",
        'start': "1970-01-01T00:00:00",
        'deadline': "1970-01-01T00:00:30"
    }


@pytest.fixture(params=['post_budget', 'banner_budget'])
def budget(request):
    return request.getfuncargvalue(request.param)


@pytest.fixture(scope="function")
def budgets(post_budget, banner_budget):
    return [post_budget, banner_budget]
