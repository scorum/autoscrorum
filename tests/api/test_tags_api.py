import time

import pytest

from src.node import Node
from src.wallet import Wallet
from tests.common import parallel_create_posts, DEFAULT_WITNESS, validate_response
from tests.data import (
    alice_post, bob_post, initdelegate_post, only_posts, post_with_comments, post_with_multilvl_comments
)


def test_get_discussions_by_created(wallet: Wallet):
    validate_response(wallet.post_comment(**alice_post), wallet.post_comment.__name__)
    validate_response(wallet.post_comment(**bob_post), wallet.post_comment.__name__)

    posts = wallet.get_discussions_by(
        "created", **{"tags": ["hockey", "football"], "limit": 100, "tags_logical_and": False}
    )
    validate_response(posts, wallet.get_discussions_by.__name__)
    assert len(posts) == 2
    # check that returned latest created post
    assert posts[0]["permlink"] == "bob-post" and posts[0]["author"] == "bob", \
        "Posts were not created in correct order"
    assert posts[1]["permlink"] == "alice-post" and posts[1]["author"] == "alice", \
        "Posts were not created in correct order"


def test_get_discussions_by_created_same_block(wallet: Wallet, node: Node):
    posts = [alice_post, bob_post]
    wallet.get_block(2, wait_for_block=True)
    # ugly workaround to create posts within same block
    result = parallel_create_posts(posts, node)
    assert 'error' not in result[0], "creation alice_post failed"
    assert 'error' not in result[1], "creation bob_post failed"
    assert result[0]["block_num"] == result[1]["block_num"], "posts are not created in single block"

    posts = wallet.get_discussions_by(
        "created", **{"tags": ["hockey", "football"], "limit": 100, "tags_logical_and": False}
    )
    assert len(posts) == 2
    # check that returned latest created post
    # as id increments after creation, so latest post should have higher id num
    assert posts[0]["id"] > posts[1]["id"], "Posts were not created in correct order"


@pytest.mark.skip_long_term
def test_get_discussions_by_author_order(wallet: Wallet):
    permlinks = ["initdelegate-post-%d" % i for i in range(1, 5)]

    post_creation_interval = int(int(wallet.get_config()["SCORUM_MIN_ROOT_COMMENT_INTERVAL"]) / 1000000)
    for permlink in permlinks:
        initdelegate_post["permlink"] = permlink
        res = wallet.post_comment(**initdelegate_post)
        validate_response(res, wallet.post_comment.__name__)
        if permlink != permlinks[-1]:
            time.sleep(post_creation_interval)  # 5 min for each post on prod

    discussions = wallet.get_discussions_by(
        "author", **{"start_author": DEFAULT_WITNESS, "limit": len(permlinks)}
    )
    total_posts = len(permlinks)
    for current in range(0, total_posts):
        opposite = total_posts - current - 1
        assert permlinks[current] == discussions[opposite]["permlink"], \
            "Broken posts order, Post %d should be on %d position." % (current, opposite)


@pytest.mark.parametrize('posts', [only_posts, post_with_comments, post_with_multilvl_comments])
def test_post_comment(wallet: Wallet, posts):
    for post in posts:
        validate_response(wallet.post_comment(**post), wallet.post_comment.__name__)


@pytest.mark.parametrize('posts', [only_posts, post_with_comments, post_with_multilvl_comments])
def test_get_content(wallet: Wallet, posts):
    for post in posts:
        wallet.post_comment(**post)
        validate_response(wallet.get_content(post['author'], post['permlink']), wallet.get_content.__name__)


@pytest.mark.parametrize('posts', [only_posts, post_with_comments, post_with_multilvl_comments])
def test_get_contents(wallet: Wallet, posts):
    for post in posts:
        wallet.post_comment(**post)

    response = wallet.get_contents([
        {"author": p["author"], "permlink": p["permlink"]}
        for p in posts
    ])

    validate_response(response, wallet.get_contents.__name__)

    assert len(response) == len(only_posts), "Should be returned all created posts and comments"


@pytest.mark.parametrize('posts', [post_with_multilvl_comments])
def test_get_comments(wallet: Wallet, posts):
    for post in posts:
        wallet.post_comment(**post)

    for i in range(1, len(posts)):
        comments = wallet.get_comments(posts[i - 1]["author"], posts[i - 1]["permlink"], i)
        validate_response(comments, wallet.get_comments.__name__)
        assert len(comments) == 1, "Should be returned single comment"
