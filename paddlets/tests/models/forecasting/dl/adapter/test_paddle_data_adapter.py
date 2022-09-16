# !/usr/bin/env python3
# -*- coding:utf-8 -*-

from paddlets.models.forecasting.dl.adapter import DataAdapter
from paddlets.models.forecasting.dl.adapter.paddle_dataset_impl import PaddleDatasetImpl
from paddlets import TSDataset, TimeSeries

import unittest
import pandas as pd
import numpy as np
import math
from typing import Dict


class TestDataAdapter(unittest.TestCase):
    def setUp(self):
        """
        unittest setup
        """
        super().setUp()

    def test_to_paddle_dataset(self):
        """
        Test DataAdapter.to_paddle_dataset()
        """
        ######################################
        # case 0 (good case)                 #
        # 1) TSDataset is valid.             #
        # 2) Use default adapter parameters. #
        ######################################
        # This is the simplest scenario for illustrating the basic usage.
        # Construct tsdataset.
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()

        # Invoke the convert method with default params.
        paddle_ds = adapter.to_paddle_dataset(paddlets_ds)
        # Start to assert
        expect_param = {
            "in_chunk_len": 1,
            "skip_chunk_len": 0,
            "out_chunk_len": 1,
            "sampling_stride": 1,
            "time_window": (1, 9)
        }
        self.assertEqual(expect_param["in_chunk_len"], paddle_ds._target_in_chunk_len)
        self.assertEqual(expect_param["skip_chunk_len"], paddle_ds._target_skip_chunk_len)
        self.assertEqual(expect_param["out_chunk_len"], paddle_ds._target_out_chunk_len)
        self.assertEqual(expect_param["sampling_stride"], paddle_ds._sampling_stride)
        self.assertEqual(expect_param["time_window"], paddle_ds._time_window)
        self._compare_if_paddlets_sample_match_paddle_sample(
            paddlets_ds=paddlets_ds,
            paddle_ds=paddle_ds,
            param=expect_param,
            future_target_is_nan=False,
            paddle_version_compatible=True
        )

        #######################################################
        # case 1 (good case)                                  #
        # 1) TSDataset is valid.                              #
        # 2) Split TSDataset to train / valid / test dataset. #
        # 3) Do NOT use default adapter parameters.           #
        #######################################################
        # Construct paddlets tsdataset
        target_periods = 12
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        common_param = {
            "in_chunk_len": 2,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1
        }
        ratio = (0.5, 0.25, 0.25)
        target_len = len(paddlets_ds.get_target().data)
        window_bias = common_param["in_chunk_len"] + \
            common_param["skip_chunk_len"] + \
            common_param["out_chunk_len"] - \
            1

        # training dataset
        train_window_min = 0 + window_bias
        train_window_max = math.ceil(target_len * sum(ratio[:1]))
        train_param = {**common_param, "time_window": (train_window_min, train_window_max)}
        train_paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **train_param)
        self.assertEqual(train_param["time_window"], train_paddle_ds._time_window)
        self._compare_if_paddlets_sample_match_paddle_sample(
            paddlets_ds=paddlets_ds,
            paddle_ds=train_paddle_ds,
            param=train_param,
            future_target_is_nan=False,
            paddle_version_compatible=True
        )

        # validation dataset
        valid_window_min = train_window_max + 1
        valid_window_max = math.ceil(target_len * sum(ratio[:2]))
        valid_param = {**common_param, "time_window": (valid_window_min, valid_window_max)}
        valid_paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **valid_param)

        self.assertEqual(valid_param["time_window"], valid_paddle_ds._time_window)
        self._compare_if_paddlets_sample_match_paddle_sample(
            paddlets_ds=paddlets_ds,
            paddle_ds=valid_paddle_ds,
            param=valid_param,
            future_target_is_nan=False,
            paddle_version_compatible=True
        )

        # test dataset
        test_window_min = valid_window_max + 1
        test_window_max = min(math.ceil(target_len * sum(ratio[:3])), target_len - 1)
        test_param = {**common_param, "time_window": (test_window_min, test_window_max)}
        test_paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **test_param)

        self.assertEqual(test_param["time_window"], test_paddle_ds._time_window)
        self._compare_if_paddlets_sample_match_paddle_sample(
            paddlets_ds=paddlets_ds,
            paddle_ds=test_paddle_ds,
            param=test_param,
            future_target_is_nan=False,
            paddle_version_compatible=True
        )

        ############################################################################################
        # case 2 (good case)                                                                       #
        # 1) TSDataset is valid.                                                                   #
        # 2) Predict scenario. The built sample only contains X, but not contains skip_chunk or Y. #
        # 3) Do NOT use default adapter parameters.                                                #
        ############################################################################################
        # Construct paddlets tsdataset
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()

        max_target_idx = len(paddlets_ds.get_target().data) - 1
        param = {
            "in_chunk_len": 2,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1,
            "time_window": (
                # max_target_idx + skip + chunk
                max_target_idx + 1 + 2,
                max_target_idx + 1 + 2
            )
        }
        # Build sample.
        paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)

        self.assertEqual(param["time_window"], paddle_ds._time_window)
        self._compare_if_paddlets_sample_match_paddle_sample(
            paddlets_ds=paddlets_ds,
            paddle_ds=paddle_ds,
            param=param,
            future_target_is_nan=True,
            paddle_version_compatible=True
        )

        ###########################################################
        # case 3 (bad case) time_window lower bound is too small. #
        ###########################################################
        # Construct paddlets tsdataset
        target_periods = 12
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        # Given the following params, the min allowed time_window lower bound can be calculated as follows:
        # min_allowed_time_window_lower_bound = (in + skip + out - 1) = 5 - 1 = 4.
        # Thus, the invalid (too small) time_window lower bound values are 0, 1, 2, 3.
        common_param = {
            "in_chunk_len": 2,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1
        }

        # time_window[0] = 3, too small.
        param = {**common_param, "time_window": (3, len(paddlets_ds.get_target().data) - 1)}
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        # time_window[0] = 2, too small.
        param = {**common_param, "time_window": (2, len(paddlets_ds.get_target().data) - 1)}
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        # time_window[0] = 1, too small.
        param = {**common_param, "time_window": (1, len(paddlets_ds.get_target().data) - 1)}
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        # time_window[0] = 0, too small.
        param = {**common_param, "time_window": (0, len(paddlets_ds.get_target().data) - 1)}
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        ###########################################################
        # case 4 (bad case) time_window upper bound is too large. #
        ###########################################################
        # Construct paddlets tsdataset
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()

        # Given the following params, the max allowed time_window upper bound can be calculated as follows:
        # max_allowed_time_window_lower_bound = (target_ts_len + skip + out - 1) = 10 + 1 + 2 - 1 = 12
        # Thus, any values which are larger than 12 will be invalid.
        param = {
            "in_chunk_len": 2,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1,
            "time_window": (
                2,
                # 13 > 12, too large.
                len(paddlets_ds.get_target().data) + 1 + 2 - 1 + 1
            )
        }
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        ###############################################
        # case 5 (bad case) TSDataset.target is None. #
        ###############################################
        # Construct paddlets tsdataset
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)
        # target is None.
        paddlets_ds._target = None

        # Initialize adapter
        adapter = DataAdapter()
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        #######################################
        # case 6 (bad case) in_chunk_len < 1. #
        #######################################
        # Construct paddlets tsdataset
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, in_chunk_len=0)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        #########################################
        # case 7 (bad case) skip_chunk_len < 0. #
        #########################################
        # Construct paddlets tsdataset
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, skip_chunk_len=-1)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        ########################################
        # case 8 (bad case) out_chunk_len < 1. #
        ########################################
        # Construct paddlets tsdataset
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, out_chunk_len=0)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        ##########################################
        # case 9 (bad case) sampling_stride < 1. #
        ##########################################
        # Construct paddlets tsdataset
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, sampling_stride=0)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        #############################################################
        # case 10 (bad case)                                        #
        # 1) Given time_window[1] <= max_target_idx                 #
        # 2) (bad) TSDataset.known_cov.time_index[-1] is too small. #
        #############################################################
        # Construct paddlets tsdataset
        target_periods = 10
        observed_periods = target_periods

        # Let max_known_timestamp be the max timestamp in the existing known_cov.time_index,
        # window_upper_bound_timestamp be the timestamp in the target.time_index which time_window[1] pointed to.
        # The following inequation MUST be held:
        # max_known_timestamp >= window_upper_bound_timestamp
        #
        # Given the following:
        # target_periods = 10
        # target_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00, 9:00]
        # known_periods = target_periods - 1 = 9
        # known_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00]
        # time_window = (3, 9)
        #
        # Firstly, compute window_upper_bound_timestamp:
        # window_upper_bound_timestamp = target_timeindex[time_window[1]] = target_timeindex[9] = 9:00
        #
        # Secondly, compute max_known_timestamp:
        # max_known_timestamp = known_timeindex[-1] = 8:00
        #
        # Finally, compare:
        # max_known_timestamp (i.e. 8:00) < window_upper_bound_timestamp (i.e. 9:00)
        #
        # According to the compare result, the max timestamp of the given known_ts is too small to build samples.
        # End.
        known_periods = target_periods - 1
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        param = {
            "in_chunk_len": 1,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1,
            "time_window": (3, 9)
        }
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        #############################################################
        # case 11 (bad case)                                        #
        # 1) Given time_window[1] > max_target_idx.                 #
        # 2) (bad) TSDataset.known_cov.time_index[-1] is too small. #
        #############################################################
        # Construct paddlets tsdataset
        target_periods = 10
        observed_periods = target_periods

        # Let max_known_timestamp be the max timestamp in the existing known_cov.time_index,
        # window_upper_bound_timestamp be the timestamp in the target.time_index which time_window[1] pointed to,
        # max_target_timestamp be the timestamp of the target.time_index.
        #
        # Before start, we should be aware of the following:
        # To test a "too small known cov" scenario, there are 2 sub-scenarios:
        # Sub-scenario 1:
        # max_known_timestamp < max_target_timestamp < window_upper_bound_timestamp
        # In this scenario, we do not need to compare the max_known_timestamp with window_upper_bound_timestamp,
        # but instead just need to compare max_known_timestamp with max_target_timestamp.
        #
        # Sub-scenario 2:
        # max_target_timestamp < max_known_timestamp < window_upper_bound_timestamp
        # In this scenario, because max_target_timestamp is smaller than max_known_timestamp, so we must compare
        # max_known_timestamp with window_upper_bound_timestamp.
        #
        # This case focus on the Sub-scenario 1, the latter case (i.e. case 12) will focus on the sub-scenario 2.
        #
        # Now start to test. In this case, the following inequation MUST be held:
        # max_known_timestamp >= max_target_timestamp
        #
        # Given the following:
        # target_periods = 10
        # target_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00, 9:00]
        # known_periods = target_periods - 1 = 9
        # known_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00]
        # time_window = (12, 12)
        #
        # Firstly, compute max_target_timestamp:
        # max_target_timestamp = target_timeindex[-1] = 9:00
        #
        # Secondly, compute max_known_timestamp:
        # max_known_timestamp = known_timeindex[-1] = 8:00
        #
        # Finally), compare:
        # max_known_timestamp (i.e. 8:00) < max_target_timestamp (i.e. 9:00)
        #
        # According to the compare result, the max timestamp of the given known_ts is too small to build samples.
        # End.
        known_periods = target_periods - 1
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        param = {
            "in_chunk_len": 1,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1,
            "time_window": (12, 12)
        }
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        #############################################################
        # case 12 (bad case)                                        #
        # 1) Given time_window[1] > max_target_idx.                 #
        # 2) (bad) TSDataset.known_cov.time_index[-1] is too small. #
        #############################################################
        # 构造paddlets tsdataset
        target_periods = 10
        observed_periods = target_periods

        # Let max_known_timestamp be the max timestamp in the existing known_cov.time_index,
        # window_upper_bound_timestamp be the timestamp in the target.time_index which time_window[1] pointed to,
        # max_target_timestamp be the timestamp of the target.time_index.
        #
        # Before start, we should be aware of the following:
        # To test a "too small known cov" scenario, there are 2 sub-scenarios:
        # Sub-scenario 1:
        # max_known_timestamp < max_target_timestamp < window_upper_bound_timestamp
        # In this scenario, we do not need to compare the max_known_timestamp with window_upper_bound_timestamp,
        # but instead just need to compare max_known_timestamp with max_target_timestamp.
        #
        # Sub-scenario 2:
        # max_target_timestamp < max_known_timestamp < window_upper_bound_timestamp
        # In this scenario, because max_target_timestamp is smaller than max_known_timestamp, so we must compare
        # max_known_timestamp with window_upper_bound_timestamp.
        #
        # This case focus on the Sub-scenario 2, the former case (i.e. case 11) already handled the sub-scenario 1.
        #
        # Now start to test. In this case, the following inequation MUST be held:
        # max_known_timestamp >= window_upper_bound_timestamp
        #
        # Given the following:
        # target_periods = 10
        # target_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00, 9:00]
        # known_periods = target_periods + 1 = 11
        # known_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00, 9:00, 10:00]
        # time_window = (12, 12)
        #
        # Firstly, compute window_upper_bound_timestamp:
        # max_target_timestamp = target_timeindex[-1] = 9:00
        # extra_timestamp_num = time_window[1] - len(target_timeindex) = 12 - 10 = 2
        # window_upper_bound_timestamp = max_target_timestamp + extra_timestamp_num = 9:00 + 2 = 11:00
        #
        # Secondly, compute max_known_timestamp:
        # max_known_timestamp = known_cov_timeindex[-1] = 10:00
        #
        # Finally), compare:
        # max_known_timestamp (i.e. 10:00) < window_upper_bound_timestamp (i.e. 11:00)
        #
        # According to the compare result, the max timestamp of the given known_ts is too small to build samples.
        # End.
        known_periods = 11
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # 初始化 adapter
        adapter = DataAdapter()
        param = {
            # in > 0, 因此是非lag场景
            "in_chunk_len": 1,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1,
            # known_cov长度=11 小于window[1]
            "time_window": (12, 12)
        }
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        ################################################################
        # case 13 (bad case)                                           #
        # 1) time_window[1] > max_target_idx.                          #
        # 2) (bad) TSDataset.observed_cov.time_index[-1] is too small. #
        ################################################################
        # Construct paddlets tsdataset
        target_periods = 10
        known_periods = target_periods + 10

        # Let max_observed_timestamp be the max timestamp in the existing observed_cov.time_index,
        # max_target_timestamp be the timestamp of the target.time_index.
        # As time_window[1] > max_target_idx, thus the following inequation MUST be held:
        # max_observed_timestamp >= max_target_timestamp
        #
        # Given the following:
        # target_periods = 10
        # target_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00, 9:00]
        # observed_periods = target_periods - 1 = 9
        # observed_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00]
        # time_window = (12, 12)
        #
        # Firstly, compute max_target_timestamp:
        # max_target_timestamp = target_timeindex[-1] = 9:00
        #
        # Secondly, compute max_observed_timestamp:
        # max_observed_timestamp = target_timeindex[-1] = 8:00
        #
        # Finally, compare:
        # max_observed_timestamp (i.e. 8:00) < max_target_timestamp (i.e. 9:00)
        #
        # According to the compare result, the max timestamp of the given observed_ts is too small to build samples.
        # End.
        observed_periods = target_periods - 1
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # 初始化 adapter
        adapter = DataAdapter()
        param = {
            # in > 0, 因此是非lag场景
            "in_chunk_len": 1,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1,
            # observed_cov 的校验不需要考虑 time_window[1] 是否超过 max_target_idx, 因为判断逻辑都一样.
            "time_window": (12, 12)
        }
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

        ################################################################
        # case 14 (bad case)                                           #
        # 1) time_window[1] <= max_target_idx.                          #
        # 2) (bad) TSDataset.observed_cov.time_index[-1] is too small. #
        ################################################################
        target_periods = 10

        # Let max_observed_timestamp be the max timestamp in the existing observed_cov.time_index,
        # window_upper_bound_timestamp be the timestamp in the target.time_index which time_window[1] pointed to,
        # last_sample_past_target_tail_timestamp be the timestamp in the target.time_index which the tail index of the
        # past_target chunk pointed to.
        # As time_window[1] <= max_target_idx, thus the following inequation MUST be held:
        # max_observed_timestamp >= last_sample_past_target_tail_timestamp
        #
        # Given the following:
        # target_periods = 10
        # target_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00, 5:00, 6:00, 7:00, 8:00, 9:00]
        # observed_periods = 5
        # observed_timeindex = [0:00, 1:00, 2:00, 3:00, 4:00]
        # time_window = (3, 8)
        #
        # Firstly, compute window_upper_bound_timestamp:
        # window_upper_bound_timestamp = target_timeindex[time_window[1]] = target_timeindex[8] = 8:00
        #
        # Secondly, compute last_sample_past_target_tail_timestamp:
        # last_sample_past_target_tail = window[1] - out_chunk_len - skip_chunk_len = 8 - 2 - 1 = 5
        # last_sample_past_target_tail_timestamp = target_timeindex[last_sample_past_target_tail]
        #                                        = target_timeindex[5]
        #                                        = 5:00
        #
        # Thirdly, compute max_observed_timestamp:
        # max_observed_timestamp = observed_time_index[-1] = 4:00
        #
        # Finally, compare:
        # max_observed_timestamp (i.e. 4:00) < last_sample_past_target_tail_timestamp (i.e. 5:00)
        #
        # According to the compare result, the max timestamp of the given observed_ts is too small to build samples.
        # End.
        observed_periods = 5
        known_periods = target_periods + 10
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        # Initialize adapter
        adapter = DataAdapter()
        param = {
            "in_chunk_len": 1,
            "skip_chunk_len": 1,
            "out_chunk_len": 2,
            "sampling_stride": 1,
            "time_window": (3, 8)
        }
        succeed = True
        try:
            paddle_ds = adapter.to_paddle_dataset(paddlets_ds, **param)
        except Exception as e:
            succeed = False
        self.assertFalse(succeed)

    def test_to_paddle_dataloader(self):
        """
        Test DataAdapter.to_paddle_dataloader()
        """
        ################################
        # case 0 (good case)           #
        # 1) known_cov is NOT None.    #
        # 2) observed_cov is NOT None. #
        ################################
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)

        adapter = DataAdapter()
        paddle_ds = adapter.to_paddle_dataset(paddlets_ds)
        batch_size = 2
        paddle_dataloader = adapter.to_paddle_dataloader(paddle_ds, batch_size, shuffle=False)

        all_keys = {"past_target", "future_target", "known_cov", "observed_cov"}
        for batch_idx, batch_dict in enumerate(paddle_dataloader):
            curr_batch_size = list(batch_dict.values())[0].shape[0]
            for sample_idx in range(curr_batch_size):
                dataset_sample = paddle_ds[batch_idx * batch_size + sample_idx]
                for key in all_keys:
                    dataloader_ndarray_sample = batch_dict[key][sample_idx].numpy()
                    dataset_ndarray_sample = dataset_sample[key]
                    self.assertTrue(np.alltrue(dataloader_ndarray_sample == dataset_ndarray_sample))

        ################################
        # case 1 (good case)           #
        # 1) known_cov is None.        #
        # 2) observed_cov is NOT None. #
        ################################
        # This is an expected scenario because it is not mandatory for a model to use known covariates as features.
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)
        # Explicitly set known timeseries to None.
        paddlets_ds._known_cov = None

        adapter = DataAdapter()
        paddle_ds = adapter.to_paddle_dataset(paddlets_ds)
        batch_size = 2
        paddle_dataloader = adapter.to_paddle_dataloader(paddle_ds, batch_size, shuffle=False)

        all_keys = {"past_target", "future_target", "known_cov", "observed_cov"}
        good_keys = {"past_target", "future_target", "observed_cov"}
        none_keys = all_keys - good_keys
        for batch_idx, batch_dict in enumerate(paddle_dataloader):
            curr_batch_size = list(batch_dict.values())[0].shape[0]
            for sample_idx in range(curr_batch_size):
                dataset_sample = paddle_ds[batch_idx * batch_size + sample_idx]
                for key in all_keys:
                    if key in none_keys:
                        self.assertTrue(key not in dataset_sample.keys())
                        continue

                    # good keys
                    dataloader_ndarray_sample = batch_dict[key][sample_idx].numpy()
                    dataset_ndarray_sample = dataset_sample[key]
                    self.assertTrue(np.alltrue(dataloader_ndarray_sample == dataset_ndarray_sample))

        #############################
        # case 2 (good case)        #
        # 1) known_cov is NOT None. #
        # 2) observed_cov is None.  #
        #############################
        # This is an expected scenario because it is not mandatory for a model to use observed covariates as features.
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)
        # Explicitly set observed timeseries to None.
        paddlets_ds._observed_cov = None

        adapter = DataAdapter()
        paddle_ds = adapter.to_paddle_dataset(paddlets_ds)
        batch_size = 2
        paddle_dataloader = adapter.to_paddle_dataloader(paddle_ds, batch_size, shuffle=False)

        all_keys = {"past_target", "future_target", "known_cov", "observed_cov"}
        good_keys = {"past_target", "future_target", "known_cov"}
        none_keys = all_keys - good_keys
        for batch_idx, batch_dict in enumerate(paddle_dataloader):
            curr_batch_size = list(batch_dict.values())[0].shape[0]
            for sample_idx in range(curr_batch_size):
                dataset_sample = paddle_ds[batch_idx * batch_size + sample_idx]
                for key in all_keys:
                    if key in none_keys:
                        self.assertTrue(key not in dataset_sample.keys())
                        continue

                    # good keys
                    dataloader_ndarray_sample = batch_dict[key][sample_idx].numpy()
                    dataset_ndarray_sample = dataset_sample[key]
                    self.assertTrue(np.alltrue(dataloader_ndarray_sample == dataset_ndarray_sample))

        ############################
        # case 3 (good case)       #
        # 1) known_cov is None.    #
        # 2) observed_cov is None. #
        ############################
        # This is an expected scenario because it is not mandatory for a model to use known / observed covariates
        # as features.
        target_periods = 10
        known_periods = target_periods + 10
        observed_periods = target_periods
        paddlets_ds = self._build_mock_ts_dataset(target_periods, known_periods, observed_periods)
        # Explicitly set known and observed timeseries to None.
        paddlets_ds._known_cov = None
        paddlets_ds._observed_cov = None

        adapter = DataAdapter()
        paddle_ds = adapter.to_paddle_dataset(paddlets_ds)
        batch_size = 2
        paddle_dataloader = adapter.to_paddle_dataloader(paddle_ds, batch_size, shuffle=False)

        all_keys = {"past_target", "future_target", "known_cov", "observed_cov"}
        good_keys = {"past_target", "future_target"}
        none_keys = all_keys - good_keys
        for batch_idx, batch_dict in enumerate(paddle_dataloader):
            curr_batch_size = list(batch_dict.values())[0].shape[0]
            for sample_idx in range(curr_batch_size):
                dataset_sample = paddle_ds[batch_idx * batch_size + sample_idx]
                for key in all_keys:
                    if key in none_keys:
                        self.assertTrue(key not in dataset_sample.keys())
                        continue

                    # good keys
                    dataloader_ndarray_sample = batch_dict[key][sample_idx].numpy()
                    dataset_ndarray_sample = dataset_sample[key]
                    self.assertTrue(np.alltrue(dataloader_ndarray_sample == dataset_ndarray_sample))

    def _build_mock_ts_dataset(self, target_periods, known_periods, observed_periods):
        """Build mock paddlets dataset"""
        target_df = pd.Series(
            [i for i in range(target_periods)],
            index=pd.date_range("2022-01-01", periods=target_periods, freq="1D"),
            name="target0"
        )

        known_cov_df = pd.DataFrame(
            [(i * 10, i * 100) for i in range(known_periods)],
            index=pd.date_range("2022-01-01", periods=known_periods, freq="1D"),
            columns=["known0", "known1"]
        )

        observed_cov_df = pd.DataFrame(
            [(i * -1, i * -10) for i in range(observed_periods)],
            index=pd.date_range("2022-01-01", periods=observed_periods, freq="1D"),
            columns=["past0", "past1"]
        )

        return TSDataset(
            target=TimeSeries.load_from_dataframe(data=target_df),
            known_cov=TimeSeries.load_from_dataframe(data=known_cov_df),
            observed_cov=TimeSeries.load_from_dataframe(data=observed_cov_df),
            static_cov={"static0": 1, "static1": 2}
        )

    def _compare_if_paddlets_sample_match_paddle_sample(
        self,
        paddlets_ds: TSDataset,
        paddle_ds: PaddleDatasetImpl,
        param: Dict,
        future_target_is_nan: bool = False,
        paddle_version_compatible: bool = False
    ) -> None:
        """
        Given a TSDataset and a built paddle.io.Dataset, compare if these data are matched.

        Args:
            paddlets_ds(TSDataset): Raw TSDataset.
            paddle_ds(PaddleDatasetImpl): Built paddle.io.Dataset.
            param(Dict): param for building samples.
            future_target_is_nan(bool, optional): Set to True to indicates that the label (i.e. Y) of the built
                sample(s) are np.NaN. Default is False.
            paddle_version_compatible(bool, optional): Set to True to be compatible with old paddle version. Default
                is False.
        """
        in_chunk_len = param["in_chunk_len"]
        skip_chunk_len = param["skip_chunk_len"]
        out_chunk_len = param["out_chunk_len"]
        sampling_stride = param["sampling_stride"]
        time_window = param["time_window"]
        target_ts = paddlets_ds.get_target()
        known_ts = paddlets_ds.get_known_cov()
        observed_ts = paddlets_ds.get_observed_cov()

        for sidx in range(len(paddle_ds.samples)):
            curr_paddle_sample = paddle_ds[sidx]

            # past_target
            paddle_past_target = curr_paddle_sample["past_target"]
            paddlets_past_target_tail = time_window[0] + sidx * sampling_stride - skip_chunk_len - out_chunk_len
            paddlets_past_target = \
                target_ts.to_numpy(False)[paddlets_past_target_tail - in_chunk_len + 1:paddlets_past_target_tail + 1]

            self.assertTrue(np.alltrue(paddlets_past_target == paddle_past_target))

            # future_target
            paddle_future_target = curr_paddle_sample["future_target"]
            # Built sample does NOT contain Y, i.e. the chunk is filled with np.NaN.
            if future_target_is_nan is True:
                self.assertEqual(out_chunk_len, paddle_future_target.shape[0])
                # No matter the built samples contain Y or not, the shape[0] of future_target will always be equal to
                # out_chunk_len. The only diff is that for predict scenario, the future_target ndarray will be filled
                # with np.NaN, while for fit scenario, it will be filled with the actual future target time series data.
                self.assertTrue(np.alltrue(np.isnan(paddle_future_target)))

            # Built samples contain Y.
            else:
                paddlets_future_target_tail = time_window[0] + (sidx * sampling_stride) + 1
                paddlets_future_target_head = paddlets_future_target_tail - out_chunk_len
                paddlets_future_target = target_ts.to_numpy(False)[paddlets_future_target_head:paddlets_future_target_tail]
                self.assertTrue(np.alltrue(paddlets_future_target == paddle_future_target))

            # known_cov
            paddle_known_cov = curr_paddle_sample["known_cov"]
            if paddlets_ds.get_known_cov() is not None:
                paddlets_known_cov_right_tail = time_window[0] + (sidx * sampling_stride) + 1
                paddlets_known_cov_right_head = paddlets_known_cov_right_tail - out_chunk_len
                paddlets_known_cov_right = known_ts.to_numpy(False)[paddlets_known_cov_right_head:paddlets_known_cov_right_tail]

                paddlets_known_cov_left_tail = paddlets_known_cov_right_head - 1 - skip_chunk_len + 1
                paddlets_known_cov_left_head = paddlets_known_cov_left_tail - in_chunk_len
                paddlets_known_cov_left = known_ts.to_numpy(False)[paddlets_known_cov_left_head:paddlets_known_cov_left_tail]

                paddlets_known_cov = np.vstack((paddlets_known_cov_left, paddlets_known_cov_right))
                self.assertTrue(np.alltrue(paddlets_known_cov == paddle_known_cov))
            # known_cov is None.
            else:
                self.assertTrue("known_cov" not in curr_paddle_sample.keys())

            # observed_cov
            paddle_observed_cov = curr_paddle_sample["observed_cov"]
            if paddlets_ds.get_observed_cov() is not None:
                paddlets_observed_cov_tail = time_window[0] + sidx * sampling_stride - skip_chunk_len - out_chunk_len
                paddlets_observed_cov = \
                    observed_ts.to_numpy(False)[paddlets_observed_cov_tail - in_chunk_len + 1:paddlets_observed_cov_tail + 1]
                self.assertTrue(np.alltrue(paddlets_observed_cov == paddle_observed_cov))
            # observed_cov is None.
            else:
                self.assertTrue("observed_cov" not in curr_paddle_sample.keys())
