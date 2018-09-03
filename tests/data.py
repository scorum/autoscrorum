from tests.common import DEFAULT_WITNESS

alice_post = {
    'author': 'alice',
    'permlink': 'alice-post',
    'parent_author': '',
    'parent_permlink': 'football',
    'title': 'alice football title',
    'body': 'alice football body',
    'json_metadata': '{"tags":["football"]}'
}

bob_post = {
    'author': 'bob',
    'permlink': 'bob-post',
    'parent_author': '',
    'parent_permlink': 'hockey',
    'title': 'bob hockey title',
    'body': 'bob hockey body',
    'json_metadata': '{"tags":["hockey"]}'
}

initdelegate_post = {
    'author': DEFAULT_WITNESS,
    'permlink': 'initdelegate-post',
    'parent_author': '',
    'parent_permlink': 'football',
    'title': 'initdelegate post title',
    'body': 'initdelegate post body',
    'json_metadata': '{"tags":["first_tag", "football", "initdelegate_posts"]}'
}

only_posts = [alice_post, bob_post, initdelegate_post]

bob_comment_lv1 = {
    'author': 'bob',
    'permlink': 'bob-comment-1',
    'parent_author': initdelegate_post["author"],
    'parent_permlink': initdelegate_post["permlink"],
    'title': 'bob comment title',
    'body': 'bob comment body',
    'json_metadata': '{"tags":["comment", "initdelegate_posts", "bob_tag"]}'
}

alice_comment_lv1 = {
    'author': 'alice',
    'permlink': 'alice-comment-1',
    'parent_author': initdelegate_post["author"],
    'parent_permlink': initdelegate_post["permlink"],
    'title': 'alice comment title',
    'body': 'alice comment body',
    'json_metadata': '{"tags":["comment", "initdelegate_posts", "alice_tag"]}'
}

post_with_comments = [initdelegate_post, bob_comment_lv1, alice_comment_lv1]

alice_comment_lv2 = {
    'author': 'alice',
    'permlink': 'alice-comment-2',
    'parent_author': bob_comment_lv1["author"],
    'parent_permlink': bob_comment_lv1["permlink"],
    'title': 'alice comment_2 title',
    'body': 'alice comment_2 body',
    'json_metadata': '{"tags":["comment", "initdelegate_posts", "alice_tag"]}'
}

post_with_multilvl_comments = [initdelegate_post, bob_comment_lv1, alice_comment_lv2]
