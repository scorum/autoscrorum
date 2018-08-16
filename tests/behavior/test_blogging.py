import datetime

from src.wallet import Wallet


def test_post_comment(wallet: Wallet):
    post_kwargs = {'author': 'initdelegate',
                   'permlink': 'initdelegate-post-1',
                   'parent_author': '',
                   'parent_permlink': 'football',
                   'title': 'initdelegate post title',
                   'body': 'initdelegate post body',
                   'json_metadata': '{"tags":["first_tag", "football", "initdelegate_posts"]}'}
    comment_level_1_kwargs = {'author': 'bob',
                              'permlink': 'bob-comment-1',
                              'parent_author': 'initdelegate',
                              'parent_permlink': 'initdelegate-post-1',
                              'title': 'bob comment title',
                              'body': 'bob comment body',
                              'json_metadata': '{"tags":["comment", "initdelegate_posts", "bob_tag"]}'}
    comment_level_2_kwargs = {'author': 'alice',
                              'permlink': 'alice-comment-1',
                              'parent_author': 'bob',
                              'parent_permlink': 'bob-comment-1',
                              'title': 'alice comment title',
                              'body': 'alice comment body',
                              'json_metadata': '{"tags":["comment", "initdelegate_posts", "alice_tag"]}'}

    assert 'error' not in wallet.post_comment(**post_kwargs).keys(), 'post creation failed'
    assert 'error' not in wallet.post_comment(**comment_level_1_kwargs).keys(), 'post creation failed'
    assert 'error' not in wallet.post_comment(**comment_level_2_kwargs).keys(), 'post creation failed'

    time_config = wallet.get_config()

    def validate_cashout_interval(comment: dict):
        time_format = '%Y-%m-%dT%H:%M:%S'
        date_start = datetime.datetime.strptime(comment['created'], time_format)
        date_finish = datetime.datetime.strptime(comment['cashout_time'], time_format)
        delta = date_finish - date_start
        cashout_window = int(time_config["SCORUM_CASHOUT_WINDOW_SECONDS"])
        assert delta.total_seconds() == cashout_window

    def validate_url(comment: dict):
        if comment['parent_author']:
            assert comment['url'] == '/{category}/@{root_author}/{root_permlink}#@{author}/{permlink}' \
                .format(category=comment['category'],
                        root_author=post['author'],
                        root_permlink=post['permlink'],
                        author=comment['author'],
                        permlink=comment['permlink'])
        else:
            assert comment['url'] == '/{}/@{}/{}'.format(comment['category'], comment['author'], comment['permlink'])

    def validate_comment(comment, comment_kwargs, parent=None):
        print(comment)
        for key, value in comment_kwargs.items():
            assert comment[key] == value, '{} value differs from expected'.format(key)
        assert comment['category'] == post_kwargs['parent_permlink']
        expected_depth = parent['depth'] + 1 if parent else 0
        assert comment['depth'] == expected_depth
        assert comment['root_title'] == post_kwargs['title']
        assert comment['root_comment'] == post['id']
        validate_cashout_interval(comment)
        validate_url(comment)

    post = wallet.get_content(post_kwargs['author'], post_kwargs['permlink'])
    validate_comment(post, post_kwargs)

    comment_level_1 = wallet.get_comments(post_kwargs['author'], post_kwargs['permlink'], 1)
    assert len(comment_level_1) == 1, 'get_content_replies method should return only 1 level children'
    validate_comment(comment_level_1[0], comment_level_1_kwargs, post)

    comment_level_2 = wallet.get_comments(comment_level_1_kwargs['author'], comment_level_1_kwargs['permlink'], 2)[0]
    validate_comment(comment_level_2, comment_level_2_kwargs, comment_level_1[0])
