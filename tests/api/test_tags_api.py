import time

import pytest
import json

from src.node import Node
from src.wallet import Wallet
from tests.common import parallel_create_posts, DEFAULT_WITNESS, validate_response


def test_get_discussions_by_created(wallet: Wallet, alice_post, bob_post):
    validate_response(wallet.post_comment(**alice_post), wallet.post_comment.__name__)
    validate_response(wallet.post_comment(**bob_post), wallet.post_comment.__name__)

    posts = wallet.get_discussions_by(
        "created", **{"tags": ["hockey", "football"], "limit": 100, "tags_logical_and": False}
    )
    validate_response(posts, wallet.get_discussions_by.__name__ + "_created")
    assert len(posts) == 2
    # check that returned latest created post
    assert posts[0]["permlink"] == "bob-post" and posts[0]["author"] == "bob", \
        "Posts were not created in correct order"
    assert posts[1]["permlink"] == "alice-post" and posts[1]["author"] == "alice", \
        "Posts were not created in correct order"


def test_get_discussions_by_created_same_block(wallet: Wallet, node: Node, alice_post, bob_post):
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


@pytest.mark.parametrize(
    'by_tags,exclude_tags,expected_cnt',
    [
        (["sport"], ["hockey"], 2), (["sport"], ["football"], 1), (["test"], ["sport"], 0),
        (["sport"], ["hockey", "first_tag"], 1), (["football"], ["sport"], 0)
    ]
)
def test_get_discussions_by_created_exclude_tags(wallet: Wallet, by_tags, exclude_tags, expected_cnt, only_posts):
    for post in only_posts:
        wallet.post_comment(**post)

    posts = wallet.get_discussions_by(
        "created", **{
            "tags": by_tags, "limit": 100, "tags_logical_and": False, "exclude_tags": exclude_tags
        }
    )
    validate_response(posts, wallet.get_discussions_by.__name__)
    assert len(posts) == expected_cnt
    for post in posts:
        tags = set(json.loads(post["json_metadata"])["tags"])
        assert not tags.intersection(set(exclude_tags))


@pytest.mark.skip_long_term
def test_get_discussions_by_author_order(wallet: Wallet, initdelegate_post):
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
    validate_response(discussions, "get_discussions_by_author")
    total_posts = len(permlinks)
    for current in range(0, total_posts):
        opposite = total_posts - current - 1
        assert permlinks[current] == discussions[opposite]["permlink"], \
            "Broken posts order, Post %d should be on %d position." % (current, opposite)


def test_get_content(wallet: Wallet, posts):
    for post in posts:
        wallet.post_comment(**post)
        validate_response(wallet.get_content(post['author'], post['permlink']), wallet.get_content.__name__)


def test_get_contents(wallet: Wallet, posts):
    for post in posts:
        wallet.post_comment(**post)

    response = wallet.get_contents([
        {"author": p["author"], "permlink": p["permlink"]}
        for p in posts
    ])

    validate_response(response, wallet.get_contents.__name__)

    assert len(response) == len(posts), "Should be returned all created posts and comments"


def test_get_comments(wallet: Wallet, post_with_multilvl_comments):
    posts = post_with_multilvl_comments  # ugly workaround
    for post in posts:
        wallet.post_comment(**post)

    for i in range(1, len(posts)):
        comments = wallet.get_comments(posts[i - 1]["author"], posts[i - 1]["permlink"], i)
        validate_response(comments, wallet.get_comments.__name__)
        assert len(comments) == 1, "Should be returned single comment"


@pytest.mark.skip("Method returns cashouted posts. Cashout for testnet is 2 hours")
def test_get_paid_posts_comments_by_author(wallet: Wallet, initdelegate_post):
    # REQUIREMENTS: return an array of posts and comments belonging to the given author that have reached cashout time.
    # This method should allow for pagination. The query should include field that will filter posts/comments that
    # have 0 SP rewards. The posts/comments should be sorted by last_payout field in the descending order.
    permlinks = ["initdelegate-post-%d" % i for i in range(1, 2)]

    post_creation_interval = int(int(wallet.get_config()["SCORUM_MIN_ROOT_COMMENT_INTERVAL"]) / 1000000)

    for permlink in permlinks:
        initdelegate_post["permlink"] = permlink
        res = wallet.post_comment(**initdelegate_post)
        validate_response(res, wallet.post_comment.__name__)
        # print(wallet.get_content(DEFAULT_WITNESS, permlink))
        if permlink != permlinks[-1]:
            time.sleep(post_creation_interval)  # 5 min for each post on prod

    posts = wallet.get_paid_posts_comments_by_author(**{"start_author": DEFAULT_WITNESS, "limit": len(permlinks)})

    assert len(posts) == len(permlinks)


def test_get_parents(wallet: Wallet, posts):
    for post in posts:
        wallet.post_comment(**post)
        content = wallet.get_content(post["author"], post["permlink"])
        parents = wallet.get_parents(**{"author": post["author"], "permlink": post["permlink"]})
        validate_response(parents, wallet.get_parents.__name__)
        assert len(parents) == content["depth"]
        current = post
        for parent in parents:
            assert current["parent_permlink"] == parent["permlink"]
            current = parent
