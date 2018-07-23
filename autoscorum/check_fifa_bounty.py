import datetime
import json
import logging

from autoscorum.wallet import Wallet
from graphenebase.amount import Amount
from sortedcontainers import SortedSet

FIFA_BLOCK_NUM = 3325780

# reward operations
O_AUTHOR_REWARD = "author_reward"
O_BENEFACTOR_REWARD = "comment_benefactor_reward"
O_COMMENT_REWARD = "comment_reward"
O_CURATION_REWARD = "curation_reward"

# CHAIN_ID = "d3c1f19a4947c296446583f988c43fd1a83818fabaf3454a0020198cb361ebd2"
# ADDR_BEFORE = "rpc1-testnet-v2.scorum.com:8001"
CHAIN_ID = "db4007d45f04c1403a7e66a5c66b5b1cdfc2dde8b5335d1d2f116d592ca3dbb1"
# ADDR_BEFORE = "localhost:11092"
# ADDR_BEFORE = "rpc1-mainnet-weu-v2.scorum.com:8001"
# ADDR_AFTER = ADDR_BEFORE

# ADDR_BEFORE = "192.168.100.10:8091"
# ADDR_AFTER = "192.168.100.10:8093"

ADDR_BEFORE = "localhost:8091"
ADDR_AFTER = "localhost:8093"


def get_fifa_pool(chain_id, address):
    with Wallet(chain_id, address) as wallet:
        return Amount(wallet.get_chain_capital()["content_reward_fifa_world_cup_2018_bounty_fund_sp_balance"])


def list_accounts(chain_id, address):
    with Wallet(chain_id, address) as wallet:
        limit = 100
        names = []
        last = ""
        while True:
            accs = wallet.list_accounts(limit, last)

            if len(names) == 0:
                names += accs
            else:
                names += accs[1:]

            if len(accs) < limit or names[-1] == last:
                break
            last = accs[-1]
        return names


def get_accounts(names, chain_id, address):
    with Wallet(chain_id, address) as wallet:
        accounts = wallet.get_accounts(names)
        logging.info("Total number of accounts; %d" % len(accounts))
        return {a["name"]: a for a in accounts}


def get_posts(chain_id, address):
    with Wallet(chain_id, address) as wallet:
        posts = {"%s:%s" % (p["author"], p["permlink"]): p for p in wallet.get_posts_and_comments()}
        logging.info("Total number of posts and comments: %d", len(posts))
        return posts


def get_operations_in_fifa_block(chain_id, address):
    with Wallet(chain_id, address) as w:
        operations = w.get_ops_in_block(FIFA_BLOCK_NUM, 2)
        save_to_file("operations.json", operations)
        return operations


def calc_accounts_actual_rewards(accounts, operations):
    for _, acc in accounts.items():
        acc["actual_reward"] = Amount("0 SP")
    op_num = 0
    op_sum = Amount("0 SP")
    missed_accs = set()
    for num, data in operations:
        operation = data["op"][0]
        if operation != O_AUTHOR_REWARD:
            continue
        name = data["op"][1]["author"]
        if name not in accounts:
            missed_accs.add(name)
            continue
        accounts[name]["actual_reward"] += Amount(data["op"][1]["reward"])
        op_sum += Amount(data["op"][1]["reward"])
        op_num += 1
    if missed_accs:
        logging.error("Unexpected '%d' author_reward operations for accs: %s", missed_accs)
    logging.info("Total number of author_reward operations: %d, reward sum: '%s'", op_num, str(op_sum))


def calc_posts_actual_rewards(posts, operations):
    for _, post in posts.items():
        post.update({"actual_reward": Amount("0 SP"), "commenting_reward": Amount("0 SP")})
    op_num = 0
    fund_sum = Amount("0 SP")
    commenting_sum = Amount("0 SP")
    missed_posts = set()
    for num, data in operations:
        operation = data["op"][0]
        if operation != O_COMMENT_REWARD or Amount(data["op"][1]["curators_reward"]) > Amount("0 SP"):
            continue
        author = data["op"][1]["author"]
        permlink = data["op"][1]["permlink"]
        address = "%s:%s" % (author, permlink)
        if address not in posts:
            missed_posts.add(address)
            continue
        posts[address]["actual_reward"] += Amount(data["op"][1]["fund_reward"])
        fund_sum += Amount(data["op"][1]["fund_reward"])
        posts[address]["commenting_reward"] += Amount(data["op"][1]["commenting_reward"])
        commenting_sum += Amount(data["op"][1]["commenting_reward"])
        op_num += 1
    if missed_posts:
        logging.error("Unexpected '%d' comment_reward operation for posts: %s", len(missed_posts), missed_posts)
    logging.info(
        "Total number of comment_reward operations: %d, fund_reward sum: '%s', commenting_reward sum: '%s'",
        op_num, str(fund_sum), str(commenting_sum)
    )


def load_from_file(path):
    with open(path, "r") as f:
        return json.loads(f.read())


def save_to_file(path, data):
    with open(path, "w") as f:
        f.write(json.dumps(data))


def comparison_str(expected: Amount, actual: Amount):
    delta = expected - actual
    percent = "%.2f%%" % round((actual.amount / expected.amount) * 100, 9) if expected.amount else "inf%"
    return "actual '%s', expected '%s', delta '%s', percent '%s'" % (str(actual), str(expected), str(delta), percent)


def to_date(date: str):
    return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")


def find_posts_to_be_rewarded(posts):
    for _, post in posts.items():
        post.update({"is_reward_expected": False})
    posts_to_be_rewarded = [
        address for address, post in posts.items()
        if int(post["net_rshares"]) > 0
           and to_date(post["cashout_time"]) < datetime.datetime.utcnow()
    ]
    posts_to_be_rewarded = SortedSet(posts_to_be_rewarded, key=lambda k: int(posts[k]["depth"]) * -1)
    i = 0
    while True:
        address = posts_to_be_rewarded[i]
        parent_author = posts[address]["parent_author"]
        if not parent_author:
            break
        parent_permlink = posts[address]["parent_permlink"]
        posts_to_be_rewarded.add(value="%s:%s" % (parent_author, parent_permlink))
        i += 1
    logging.info("Expected %d posts and comments to be rewarded: %s", len(posts_to_be_rewarded), posts_to_be_rewarded)
    for address in posts_to_be_rewarded:
        posts[address]["is_reward_expected"] = True


def sum_net_rshares_per_account(accounts, posts):
    for _, acc in accounts.items():
        acc.update({"net_rshares": 0, "is_reward_expected": False})
    total_net_rshares = 0
    for address in posts:
        if not posts[address]["is_reward_expected"]:
            continue
        author = posts[address]["author"]
        accounts[author]["is_reward_expected"] = True
        net_rshares = int(posts[address]["net_rshares"])
        if net_rshares > 0:
            accounts[author]["net_rshares"] += net_rshares
            total_net_rshares += net_rshares
    logging.info(
        "Expected amount of accounts to be rewarded: %d",
        len([name for name in accounts if accounts[name]["is_reward_expected"]])
    )
    return total_net_rshares


def calc_expected_reward(data, fifa_pool, total_net_rshares):
    for record in data.values():
        record["expected_reward"] = Amount("0 SP")
        if not record["is_reward_expected"]:
            continue
        net_rshares = int(record["net_rshares"])
        if net_rshares > 0:
            record["expected_reward"]["amount"] = int(fifa_pool.amount * net_rshares / total_net_rshares)


def check_comments_fund_reward_sum_after_distribution_equal_to_fifa_pull_size(posts, fifa_pool):
    fund_sum = Amount("0 SP")
    for post in posts.values():
        fund_sum += post["actual_reward"]
    msg = "Sum of actual fund rewards is not equal with fifa pool: %s" % \
          comparison_str(fifa_pool, fund_sum)
    # assert fund_sum == fifa_pool, msg
    if fund_sum == fifa_pool:
        return
    logging.error(msg)


def check_sum_of_authors_sp_balance_gain_equal_to_fifa_pool_size(accounts_before, accounts_after, fifa_pool):
    total_gain = Amount("0 SP")
    for name in accounts_before.keys():
        sp_before = Amount(accounts_before[name]["scorumpower"])
        sp_after = Amount(accounts_after[name]["scorumpower"])
        total_gain += sp_after - sp_before
    msg = "Amount of sp balance gain is not equal with fifa pool: %s" % \
          comparison_str(fifa_pool, total_gain)
    # assert total_gain == fifa_pool, msg
    if total_gain == fifa_pool:
        return
    logging.error(msg)


def check_fifa_pool_after_distribution_equal_zero(fifa_pool):
    msg = "Fifa pool after payment is not equal to zero: %s" % str(fifa_pool)
    # assert fifa_pool == Amount("0 SP"), msg
    if fifa_pool == Amount("0 SP"):
        return
    logging.error(msg)


def check_account_scr_balance_do_not_changed(account_before, account_after):
    scr_before = Amount(account_before["balance"])
    scr_after = Amount(account_after["balance"])
    msg = "Amount of SCR balance has changed for '%s'" % account_before["name"]
    # assert scr_after - scr_before == Amount("0 SCR"), msg
    if scr_after - scr_before == Amount("0 SCR"):
        return
    logging.error(msg)


def check_balances_of_expected_accounts_increased(account_before, account_after):
    net_rshares = account_before["net_rshares"]
    gain = Amount(account_after["scorumpower"]) - Amount(account_before["scorumpower"])
    is_reward_expected = account_before["is_reward_expected"]
    if is_reward_expected:
        msg = "Balance of '%s' account  with net_rshares '%d' has not changed." % (account_before["name"], net_rshares)
        # assert gain > Amount("0 SP"), msg
        if gain > Amount("0 SP"):
            return
        logging.error(msg)


def check_balances_expected_accounts_not_increased(account_before, account_after):
    net_rshares = account_before["net_rshares"]
    gain = Amount(account_after["scorumpower"]) - Amount(account_before["scorumpower"])
    is_reward_expected = account_before["is_reward_expected"]
    if not is_reward_expected:
        msg = "Account '%s' balance with net_rshares '%d' was changed on '%s'." % \
              (account_before["name"], net_rshares, str(gain))
        # assert Amount("0 SP") <= gain < Amount("1.000000000 SP"), msg
        if Amount("0 SP") <= gain < Amount("1.000000000 SP"):
            return
        logging.error(msg)


def check_accounts_fund_reward_distribution(account_before, account_after):
    expected = account_before["expected_reward"]
    actual = account_after["actual_reward"]
    msg = "Account actual and expected rewards are not equal: %s, name '%s'" % \
        (comparison_str(expected, actual), account_before["name"])
    # assert expected == actual, msg
    if expected == actual:
        return
    logging.error(msg)


def check_posts_fund_reward_distribution(posts_before, posts_after):
    for address in posts_before.keys():
        expected = posts_before[address]["expected_reward"]
        actual = posts_after[address]["actual_reward"]
        msg = "Post actual and expected rewards are not equal: %s, author_permlink '%s'" % \
            (comparison_str(expected, actual), address)
        if Amount("-0.005 SP") <= actual - expected <= Amount("0.005 SP"):
            continue
        logging.error(msg)


def check_expected_posts_received_reward(posts_before, posts_after):
    posts_to_reward = set(address for address in posts_before if posts_before[address]["is_reward_expected"])
    rewarded_posts = set(
        address for address in posts_after
        if posts_after[address]["actual_reward"] > Amount("0 SP")
            or posts_after[address]["commenting_reward"] > Amount("0 SP")
    )
    missing = posts_to_reward.difference(rewarded_posts)
    if missing:
        logging.error("Missing comment_reward_operations for %d posts: %s", len(missing), missing)
    unexpected = rewarded_posts.difference(posts_to_reward)
    if unexpected:
        logging.error("Unexpected comment_reward_operations for %d posts: %s", len(unexpected), unexpected)


def check_expected_accounts_received_reward(accounts_before, accounts_after):
    accs_to_reward = set(name for name in accounts_before if accounts_before[name]["is_reward_expected"])
    rewarded_authors = set(name for name in accounts_after if accounts_after[name]["actual_reward"] > Amount("0 SP"))
    missing = accs_to_reward.difference(rewarded_authors)
    if missing:
        logging.error("Missing author_reward_operations for %d accounts: %s", len(missing), missing)
    unexpected = rewarded_authors.difference(accs_to_reward)
    if unexpected:
        logging.error("Unexpected author_reward_operations for %d accounts: %s", len(unexpected), unexpected)


def main():
    logging.basicConfig(
        level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s.%(msecs)03d (%(name)s) %(levelname)s - %(message)s" 
    )

    logging.info("Collecting data before fifa payment.")
    names = list_accounts(CHAIN_ID, ADDR_BEFORE)
    # names = ["robin-ho"]
    accounts_before = get_accounts(names, CHAIN_ID, ADDR_BEFORE)
    posts_before = get_posts(CHAIN_ID, ADDR_BEFORE)
    find_posts_to_be_rewarded(posts_before)
    total_net_rshares = sum_net_rshares_per_account(accounts_before, posts_before)
    logging.info("Total net_rshares: %d", total_net_rshares)
    fifa_pool_before = get_fifa_pool(CHAIN_ID, ADDR_BEFORE)
    logging.info("Fifa pool before: %s" % fifa_pool_before)
    calc_expected_reward(accounts_before, fifa_pool_before, total_net_rshares)
    save_to_file("accounts_before.json", accounts_before)
    calc_expected_reward(posts_before, fifa_pool_before, total_net_rshares)
    save_to_file("posts_before.json", posts_before)

    logging.info("Collecting data after fifa payment.")
    fifa_operations = get_operations_in_fifa_block(CHAIN_ID, ADDR_AFTER)
    accounts_after = get_accounts(names, CHAIN_ID, ADDR_AFTER)
    calc_accounts_actual_rewards(accounts_after, fifa_operations)
    save_to_file("accounts_after.json", accounts_after)
    posts_after = get_posts(CHAIN_ID, ADDR_AFTER)
    calc_posts_actual_rewards(posts_after, fifa_operations)
    save_to_file("posts_after.json", posts_after)
    fifa_pool_after = get_fifa_pool(CHAIN_ID, ADDR_AFTER)
    logging.info("Fifa pool after: %s" % fifa_pool_after)

    check_expected_accounts_received_reward(accounts_before, accounts_after)
    check_expected_posts_received_reward(posts_before, posts_after)
    check_fifa_pool_after_distribution_equal_zero(fifa_pool_after)
    check_comments_fund_reward_sum_after_distribution_equal_to_fifa_pull_size(posts_after, fifa_pool_before)
    check_sum_of_authors_sp_balance_gain_equal_to_fifa_pool_size(accounts_before, accounts_after, fifa_pool_before)
    check_posts_fund_reward_distribution(posts_before,  posts_after)
    for name in names:
        check_account_scr_balance_do_not_changed(accounts_before[name], accounts_after[name])
        check_balances_of_expected_accounts_increased(accounts_before[name], accounts_after[name])
        check_balances_expected_accounts_not_increased(accounts_before[name], accounts_after[name])
        check_accounts_fund_reward_distribution(accounts_before[name], accounts_after[name])


if __name__ == "__main__":
    main()
