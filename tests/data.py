import pytest

from tests.common import DEFAULT_WITNESS

"""
############################################# Blogging Test Data #######################################################
"""


@pytest.fixture(scope="session")
def alice_post():
    return {
        'author': 'alice',
        'permlink': 'alice-post',
        'parent_author': '',
        'parent_permlink': 'football',
        'title': 'alice football title',
        'body': 'alice football body',
        'json_metadata': '{"tags":["football", "sport", "test"]}'
    }


@pytest.fixture(scope="session")
def bob_post():
    return {
        'author': 'bob',
        'permlink': 'bob-post',
        'parent_author': '',
        'parent_permlink': 'hockey',
        'title': 'bob hockey title',
        'body': 'bob hockey body',
        'json_metadata': '{"tags":["hockey", "sport", "test"]}'
    }


@pytest.fixture(scope="session")
def initdelegate_post():
    return {
        'author': DEFAULT_WITNESS,
        'permlink': 'initdelegate-post',
        'parent_author': '',
        'parent_permlink': 'football',
        'title': 'initdelegate post title',
        'body': 'initdelegate post body',
        'json_metadata': '{"tags":["first_tag", "football", "sport", "initdelegate_posts", "test"]}'
    }


@pytest.fixture(params=['alice_post', 'bob_post', 'initdelegate_post'])
def post(request):
    return request.getfuncargvalue(request.param)


@pytest.fixture(params=['alice_post', 'bob_post'])
def not_witness_post(request):
    return request.getfuncargvalue(request.param)


@pytest.fixture(scope="session")
def only_posts(alice_post, bob_post, initdelegate_post):
    return [alice_post, bob_post, initdelegate_post]


@pytest.fixture(scope="session")
def bob_comment_lv1(initdelegate_post):
    return {
        'author': 'bob',
        'permlink': 'bob-comment-1',
        'parent_author': initdelegate_post["author"],
        'parent_permlink': initdelegate_post["permlink"],
        'title': 'bob comment title',
        'body': 'bob comment body',
        'json_metadata': '{"tags":["comment", "initdelegate_posts", "bob_tag"]}'
    }


@pytest.fixture(scope="session")
def alice_comment_lv1(initdelegate_post):
    return {
        'author': 'alice',
        'permlink': 'alice-comment-1',
        'parent_author': initdelegate_post["author"],
        'parent_permlink': initdelegate_post["permlink"],
        'title': 'alice comment title',
        'body': 'alice comment body',
        'json_metadata': '{"tags":["comment", "initdelegate_posts", "alice_tag"]}'
    }


@pytest.fixture(scope="session")
def post_with_comments(initdelegate_post, bob_comment_lv1, alice_comment_lv1):
    return [initdelegate_post, bob_comment_lv1, alice_comment_lv1]


@pytest.fixture(scope="session")
def alice_comment_lv2(bob_comment_lv1):
    return {
        'author': 'alice',
        'permlink': 'alice-comment-2',
        'parent_author': bob_comment_lv1["author"],
        'parent_permlink': bob_comment_lv1["permlink"],
        'title': 'alice comment_2 title',
        'body': 'alice comment_2 body',
        'json_metadata': '{"tags":["comment", "initdelegate_posts", "alice_tag"]}'
    }


@pytest.fixture(scope="session")
def post_with_multilvl_comments(initdelegate_post, bob_comment_lv1, alice_comment_lv2):
    return [initdelegate_post, bob_comment_lv1, alice_comment_lv2]


@pytest.fixture(params=['only_posts', 'post_with_comments', 'post_with_multilvl_comments'])
def posts(request):
    return request.getfuncargvalue(request.param)


@pytest.fixture(params=['post_with_comments', 'post_with_multilvl_comments'])
def posts_comments(request):
    return request.getfuncargvalue(request.param)
