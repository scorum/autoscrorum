import time

import pytest

from src.node import Node
from src.wallet import Wallet
from tests.common import parallel_create_posts, DEFAULT_WITNESS


def test_get_discussions_by_created(wallet: Wallet):
    alice_post_kwargs = {
        'author': 'alice',
        'permlink': 'alice-post',
        'parent_author': '',
        'parent_permlink': 'football',
        'title': 'alice football title',
        'body': 'alice football body',
        'json_metadata': '{"tags":["football"]}'
    }
    bob_post_kwargs = {
        'author': 'bob',
        'permlink': 'bob-post',
        'parent_author': '',
        'parent_permlink': 'hockey',
        'title': 'bob hockey title',
        'body': 'bob hockey body',
        'json_metadata': '{"tags":["hockey"]}'
    }
    alice_post = wallet.post_comment(**alice_post_kwargs)
    bob_post = wallet.post_comment(**bob_post_kwargs)

    assert 'error' not in alice_post, "creation alice_post failed"
    assert 'error' not in bob_post, "creation bob_post failed"

    posts = wallet.get_discussions_by(
        "created", **{"tags": ["hockey", "football"], "limit": 100, "tags_logical_and": False}
    )
    assert len(posts) == 2
    # check that returned latest created post
    assert posts[0]["permlink"] == "bob-post" and posts[0]["author"] == "bob", \
        "Posts were not created in correct order"
    assert posts[1]["permlink"] == "alice-post" and posts[1]["author"] == "alice", \
        "Posts were not created in correct order"


def test_get_discussions_by_created_same_block(wallet: Wallet, node: Node):
    alice_post_kwargs = {
        'author': 'alice',
        'permlink': 'alice-post',
        'parent_author': '',
        'parent_permlink': 'football',
        'title': 'alice football title',
        'body': 'alice football body',
        'json_metadata': '{"tags":["football"]}'
    }
    bob_post_kwargs = {
        'author': 'bob',
        'permlink': 'bob-post',
        'parent_author': '',
        'parent_permlink': 'hockey',
        'title': 'bob hockey title',
        'body': 'bob hockey body',
        'json_metadata': '{"tags":["hockey"]}'
    }

    posts_kwargs = [alice_post_kwargs, bob_post_kwargs]

    wallet.get_block(2, wait_for_block=True)
    # ugly workaround to create posts within same block
    result = parallel_create_posts(posts_kwargs, node)
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
    post = {
        'author': DEFAULT_WITNESS,
        'parent_author': '',
        'parent_permlink': 'football',
        'title': 'initdelegate post title',
        'body': 'initdelegate post body',
        'json_metadata': '{"tags":["first_tag", "football", "initdelegate_posts"]}'
    }
    permlinks = ["initdelefate-post-%d" % i for i in range(1, 4)]

    post_creation_interval = int(int(wallet.get_config()["SCORUM_MIN_ROOT_COMMENT_INTERVAL"]) / 1000000)
    for permlink in permlinks:
        post["permlink"] = permlink
        res = wallet.post_comment(**post)
        assert 'error' not in res.keys(), 'post creation failed: %s' % res
        time.sleep(post_creation_interval)

    discussions = wallet.get_discussions_by(
        "author", **{"start_author": DEFAULT_WITNESS, "limit": 3, "start_permlink": permlinks[0]}
    )
    total_posts = len(permlinks)
    for current in range(0, total_posts):
        opposite = total_posts - current - 1
        assert permlinks[current] == discussions[opposite]["permlink"], \
            "Broken posts order, Post %d should be on %d position." % (current, opposite)
