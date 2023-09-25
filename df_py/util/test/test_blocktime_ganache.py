from datetime import datetime
from math import ceil

import brownie
from enforce_typing import enforce_types
from pytest import approx

from df_py.util import networkutil, oceanutil
from df_py.util.blockrange import create_range
from df_py.util.blocktime import (get_block_number_thursday,
                                  get_next_thursday_timestamp,
                                  get_st_fin_blocks, timestamp_to_block,
                                  timestr_to_block, timestr_to_timestamp)

chain = None


@enforce_types
def test_timestr_to_block_1():
    # tests here are light, the real tests are in test_*() below
    assert timestr_to_block(chain, "2022-03-29") >= 0.0
    assert timestr_to_block(chain, "2022-03-29_0:00") >= 0.0


@enforce_types
def test_timestamp_to_block_far_left():
    b = timestr_to_block(chain, "1970-01-01")
    assert b == 0 and isinstance(b, int)

    b = timestr_to_block(chain, "1970-01-01_0:00")
    assert b == 0 and isinstance(b, int)


@enforce_types
def test_timestamp_to_block_far_right():
    b = timestr_to_block(chain, "2150-01-01")
    assert b == len(chain) and isinstance(b, int)

    b = timestr_to_block(chain, "2150-01-01_0:00")
    assert b == len(chain) and isinstance(b, int)


@enforce_types
def test_timestr_to_timestamp():
    t = timestr_to_timestamp("1970-01-01_0:00")
    assert t == 0.0 and isinstance(t, float)

    t = timestr_to_timestamp("2022-03-29_17:55")
    assert t == 1648576500.0 and isinstance(t, float)

    t = timestr_to_timestamp("2022-03-29")
    assert t == 1648512000.0 and isinstance(t, float)


@enforce_types
def test_timestamp_to_block():
    # gather timestamp and blocks at block offset 0, 9, 29
    timestamp0 = chain[-1].timestamp
    block0 = chain[-1].number

    chain.mine(blocks=1, timestamp=timestamp0 + 10.0)
    timestamp1 = chain[-1].timestamp
    block1 = chain[-1].number
    assert block1 == (block0 + 1)
    assert timestamp1 == (timestamp0 + 10.0)

    chain.mine(blocks=9, timestamp=timestamp1 + 90.0)
    timestamp9 = chain[-1].timestamp
    block9 = chain[-1].number
    assert block9 == (block1 + 9)
    assert timestamp9 == (timestamp1 + 90.0)

    chain.mine(blocks=20, timestamp=timestamp9 + 200.0)
    timestamp29 = chain[-1].timestamp
    block29 = chain[-1].number
    assert block29 == (block9 + 20)
    assert timestamp29 == (timestamp9 + 200.0)

    # test
    assert timestamp_to_block(chain, timestamp0) == approx(block0, 1)
    assert timestamp_to_block(chain, timestamp9) == approx(block9, 1)
    assert timestamp_to_block(chain, timestamp29) == approx(block29, 1)

    assert timestamp_to_block(chain, timestamp0 + 10.0) == approx(block0 + 1, 1)
    assert timestamp_to_block(chain, timestamp0 + 20.0) == approx(block0 + 2, 1)

    assert timestamp_to_block(chain, timestamp9 - 10.0) == approx(block9 - 1, 1)
    assert timestamp_to_block(chain, timestamp9 + 10.0) == approx(block9 + 1, 1)

    assert timestamp_to_block(chain, timestamp29 - 10.0) == approx(block29 - 1, 1)


@enforce_types
def test_get_next_thursday():
    next_thursday = get_next_thursday_timestamp(chain)
    date = datetime.utcfromtimestamp(next_thursday)

    assert date.isoweekday() == 4


@enforce_types
def test_get_next_thursday_block_number():
    next_thursday_block = get_block_number_thursday(chain)
    assert next_thursday_block % 10 == 0
    assert len(chain) < next_thursday_block

    now = len(chain) - 1

    t0 = chain[0].timestamp
    t1 = chain[int(now)].timestamp

    avgBlockTime = (t1 - t0) / now

    next_thursday = get_next_thursday_timestamp(chain)
    apprx = (next_thursday - t0) / avgBlockTime
    apprx = ceil(apprx / 100) * 100

    assert next_thursday_block == approx(apprx, 1)


@enforce_types
def test_get_st_fin_blocks():
    chain.mine()
    # by block number
    (st, fin) = get_st_fin_blocks(chain, "0", "1")
    assert st == 0
    assert fin > 0

    # get by latest fin
    (st, fin) = get_st_fin_blocks(chain, "0", "latest")
    assert st == 0
    assert fin > 0

    # get by thu fin
    (st, fin) = get_st_fin_blocks(chain, "0", "thu")
    assert st == 0
    assert fin > 0

    # get by datetime YYYY-MM-DD
    now_date = datetime.utcfromtimestamp(chain[-1].timestamp)
    now_date = now_date.strftime("%Y-%m-%d")
    (st, fin) = get_st_fin_blocks(chain, "0", now_date)
    assert st == 0
    assert fin >= 0

    # test in conjunction with create_range in blockrange
    # to avoid extra setup in test_blockrange.py just for one test
    rng = create_range(chain, 10, 5000, 100, 42)
    assert rng


@enforce_types
def setup_function():
    networkutil.connect_dev()
    oceanutil.record_dev_deployed_contracts()
    global chain
    chain = brownie.network.chain


@enforce_types
def teardown_function():
    networkutil.disconnect()
