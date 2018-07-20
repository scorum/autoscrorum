import datetime
import json
import logging

from autoscorum.wallet import Wallet
from graphenebase.amount import Amount

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

ADDR_BEFORE = "192.168.100.10:8091"
ADDR_AFTER = "192.168.100.10:8093"

# ADDR_BEFORE = "localhost:8091"
# ADDR_AFTER = "localhost:8091"


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
        return {"%s:%s" % (p["author"], p["permlink"]): p for p in wallet.get_posts_and_comments()}


def get_accounts_rewards(accounts, chain_id, adddress):
    for _, acc in accounts.items():
        acc["actual_reward"] = Amount("0 SP")
    op_num = 0
    with Wallet(chain_id, adddress) as w:
        missed_accs = set()
        for num, data in w.get_ops_in_block(FIFA_BLOCK_NUM):
            operation = data["op"][0]
            if operation == O_AUTHOR_REWARD:
                name = data["op"][1]["author"]
                if name not in accounts:
                    missed_accs.add(name)
                    continue
                accounts[name]["actual_reward"] += Amount(data["op"][1]["reward"])
                op_num += 1
        if missed_accs:
            logging.error("Unexpected '%d' author_reward operations for accs: %s", missed_accs)
        logging.info("Total number of author_reward operations: %d", op_num)
    return accounts


def get_posts_rewards(posts, chain_id, adddress):
    for _, post in posts.items():
        post.update({"actual_reward": Amount("0 SP")})
    rewarded_authors = set()
    op_num = 0
    with Wallet(chain_id, adddress) as w:
        missed_posts = set()
        operations = w.get_ops_in_block(FIFA_BLOCK_NUM, 2)
        save_to_file("operations.json", operations)
        for num, data in operations:
            operation = data["op"][0]
            if operation == O_COMMENT_REWARD:
                author = data["op"][1]["author"]
                rewarded_authors.add(author)
                permlink = data["op"][1]["permlink"]
                address = "%s:%s" % (author, permlink)
                if address not in posts:
                    missed_posts.add(address)
                    continue
                posts[address]["actual_reward"] += Amount(data["op"][1]["fund_reward"])
                op_num += 1
        if missed_posts:
            logging.error("Unexpected '%d' comment_reward operation for posts: %s", len(missed_posts), missed_posts)
        logging.info("Total number of comment_reward operations: %d", op_num)
        logging.info("Authors received comment rewards: %d %s", len(rewarded_authors), rewarded_authors)
    return posts, rewarded_authors


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


def sum_net_rshares_per_account(accounts, posts):
    for _, acc in accounts.items():
        acc.update({"net_rshares": 0})
    total_net_rshares = 0
    for _, post in posts.items():
        author = post["author"]
        net_rshares = int(post["net_rshares"])
        cashout_time = datetime.datetime.strptime(post["cashout_time"], "%Y-%m-%dT%H:%M:%S")
        if net_rshares > 0 and cashout_time < datetime.datetime.utcnow():
            accounts[author]["net_rshares"] += net_rshares
            total_net_rshares += net_rshares
            parent_author = post.get("parent_author")
            parent_permlink = post.get("parent_permlink")
            while parent_author:
                parent = posts["%s:%s" % (parent_author, parent_permlink)]
                parent["children_reward"] = True
                accounts[parent_author]["children_reward"] = True
                parent_author = parent.get("parent_author")
                parent_permlink = parent.get("parent_permlink")
    return total_net_rshares


def get_accounts_after(names):
    accounts_after = get_accounts(names, CHAIN_ID, ADDR_AFTER)
    accounts_after = get_accounts_rewards(accounts_after, CHAIN_ID, ADDR_AFTER)
    save_to_file("accounts_after.json", accounts_after)
    return accounts_after


def calc_expected_reward(data, fifa_pool, total_net_rshares):
    for _, record in data.items():
        net_rshares = int(record["net_rshares"])
        cashout_time = datetime.datetime.strptime(
            record.get("cashout_time", "1969-12-31T23:59:59"), "%Y-%m-%dT%H:%M:%S"
        )
        # if net_rshares > 0 and cashout_time == "1969-12-31T23:59:59":
        if net_rshares > 0 and cashout_time < datetime.datetime.utcnow():
            record["expected_reward"] = Amount("0 SP")
            record["expected_reward"]["amount"] = int(fifa_pool.amount * net_rshares / total_net_rshares)
    return data


def check_comments_fund_reward_sum_after_distribution_equal_to_fifa_pull_size(accounts, fifa_pool):
    fund_sum = Amount("0 SP")
    for _, acc in accounts.items():
        fund_sum += acc["actual_reward"]
    msg = "Sum of actual fund rewards is not equal with fifa pool: %s" % \
          comparison_str(fifa_pool, fund_sum)
    # assert fund_sum == fifa_pool, msg
    if fund_sum == fifa_pool:
        return
    logging.error(msg)


def check_sum_of_authors_sp_balance_gain_equal_to_fifa_pool_size(accounts_before, accounts_after, fifa_pool):
    total_gain = Amount("0 SP")
    for name in accounts_before.keys():
        if name not in accounts_after:
            continue
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


def check_author_scr_balance_do_not_changed(account_before, account_after):
    scr_before = Amount(account_before["balance"])
    scr_after = Amount(account_after["balance"])
    msg = "Amount of SCR balance has changed for '%s'" % account_before["name"]
    # assert scr_after - scr_before == Amount("0 SCR"), msg
    if scr_after - scr_before == Amount("0 SCR"):
        return
    logging.error(msg)


def check_balances_of_authors_with_netshares_gt_zero_increased(account_before, account_after):
    net_rshares = account_before["net_rshares"]
    gain = Amount(account_after["scorumpower"]) - Amount(account_before["scorumpower"])
    children_reward = account_before.get("children_reward")
    if net_rshares > 0 or children_reward:
        msg = "Account '%s' balance with net_rshares '%d' has not changed." % (account_before["name"], net_rshares)
        # assert gain > Amount("0 SP"), msg
        if gain > Amount("0 SP"):
            return
        logging.error(msg)


def check_balances_of_authors_with_netshares_le_zero_not_increased(account_before, account_after):
    net_rshares = account_before["net_rshares"]
    gain = Amount(account_after["scorumpower"]) - Amount(account_before["scorumpower"])
    children_reward = account_before.get("children_reward")
    if net_rshares <= 0 and not children_reward:
        msg = "Account '%s' balance with net_rshares '%d' was changed on '%s'." % \
              (account_before["name"], net_rshares, str(gain))
        # assert Amount("0 SP") <= gain < Amount("1.000000000 SP"), msg
        if Amount("0 SP") <= gain < Amount("1.000000000 SP"):
            return
        logging.error(msg)


def check_authors_with_netshares_le_zero_not_have_rewards(account_before, account_after):
    net_rshares = account_before["net_rshares"]
    children_reward = account_before.get("children_reward")
    if net_rshares <= 0 and not children_reward:
        reward = account_after.get("actual_reward", Amount("0 SP"))
        msg = "Account '%s' with net_rhsraes '%d' has unexpected reward '%s'" % \
              (account_before["name"], net_rshares, str(reward))
        # assert reward == Amount("0 SP"), msg
        if reward == Amount("0 SP"):
            return
        logging.error(msg)


def check_accounts_fund_reward_distribution(account_before, account_after):
    expected = account_before.get("expected_reward", Amount("0 SP"))
    actual = account_after.get("actual_reward", Amount("0 SP"))
    msg = "Account actual and expected rewards are not equal: %s, name '%s'" % \
        (comparison_str(expected, actual), account_before["name"])
    # assert expected == actual, msg
    if expected == actual:
        return
    logging.error(msg)


def check_posts_fund_reward_distribution(posts):
    for address, post in posts.items():
        expected = post.get("expected_reward", Amount("0 SP"))
        actual = post.get("actual_reward", Amount("0 SP"))
        msg = "Post actual and expected rewards are not equal: %s, author_permlink '%s'" % \
            (comparison_str(expected, actual), address)
        if actual != expected:
            logging.error(msg)


def check_expected_authors_were_rewarded(accs_to_reward, rewarded_authors):
    missing = set(accs_to_reward).difference(set(rewarded_authors))
    if missing:
        logging.error("Missing comment_reward_operation for %d %s", len(missing), missing)
    unexpected = set(rewarded_authors).difference(set(accs_to_reward))
    if unexpected:
        logging.error("Unexpected comment_reward_operation for %d %s", len(unexpected), unexpected)


def main():
    logging.basicConfig(
        level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s.%(msecs)03d (%(name)s) %(levelname)s - %(message)s" 
    )
    names = list_accounts(CHAIN_ID, ADDR_BEFORE)
    # names = ["robin-ho"]
    # get data before
    accounts_before = get_accounts(names, CHAIN_ID, ADDR_BEFORE)
    posts = get_posts(CHAIN_ID, ADDR_BEFORE)
    total_net_rshares = sum_net_rshares_per_account(accounts_before, posts)
    logging.info("Total net_rshares: %d", total_net_rshares)
    fifa_pool_before = get_fifa_pool(CHAIN_ID, ADDR_BEFORE)
    logging.info("Fifa pool before: %s" % fifa_pool_before)
    # calc expected rewards based on net_rshares
    accounts_before = calc_expected_reward(accounts_before, fifa_pool_before, total_net_rshares)
    save_to_file("accounts_before.json", accounts_before)
    posts = calc_expected_reward(posts, fifa_pool_before, total_net_rshares)
    save_to_file("posts_before.json", posts)
    # just good to know
    num_posts_to_reward = len([
        address for address in posts
        if (int(posts[address]["net_rshares"]) > 0
            and datetime.datetime.strptime(posts[address]["cashout_time"], "%Y-%m-%dT%H:%M:%S") < datetime.datetime.utcnow())
        or posts[address].get("children_reward")
    ])
    logging.info("Expected posts to get reward: %d", num_posts_to_reward)
    accs_to_reward = set(
        name for name in accounts_before
        if accounts_before[name]["net_rshares"] > 0
        or accounts_before[name].get("children_reward")
    )
    logging.info("Expected accounts to get reward: %d %s", len(accs_to_reward), accs_to_reward)
    # get data after
    accounts_after = get_accounts_after(names)
    posts, rewarded_authors = get_posts_rewards(posts, CHAIN_ID, ADDR_AFTER)
    save_to_file("posts_after.json", posts)
    fifa_pool_after = get_fifa_pool(CHAIN_ID, ADDR_AFTER)
    logging.info("Fifa pool after: %s" % fifa_pool_after)
    # fifa checks
    check_expected_authors_were_rewarded(accs_to_reward, rewarded_authors)
    check_fifa_pool_after_distribution_equal_zero(fifa_pool_after)
    check_comments_fund_reward_sum_after_distribution_equal_to_fifa_pull_size(accounts_after, fifa_pool_before)
    check_sum_of_authors_sp_balance_gain_equal_to_fifa_pool_size(accounts_before, accounts_after, fifa_pool_before)
    check_posts_fund_reward_distribution(posts)
    for name in accounts_before.keys():
        if name not in accounts_after:
            continue
        check_author_scr_balance_do_not_changed(accounts_before[name], accounts_after[name])
        check_balances_of_authors_with_netshares_gt_zero_increased(accounts_before[name], accounts_after[name])
        check_balances_of_authors_with_netshares_le_zero_not_increased(accounts_before[name], accounts_after[name])
        check_authors_with_netshares_le_zero_not_have_rewards(accounts_before[name], accounts_after[name])
        check_accounts_fund_reward_distribution(accounts_before[name], accounts_after[name])


if __name__ == "__main__":
    main()
