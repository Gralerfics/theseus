# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import numpy as np
import pytest  # noqa: F401
import torch

import theseus.core

from .common import MockCostFunction, MockCostWeight


def test_theseus_function_init():
    all_ids = []
    variables = [theseus.core.Variable(torch.ones(1, 1), name="var_1")]
    aux_vars = [theseus.core.Variable(torch.ones(1, 1), name="aux_1")]
    for i in range(100):
        cost_weight = MockCostWeight(torch.ones(1, 1), name=f"cost_weight_{i}")
        if np.random.random() < 0.5:
            name = f"name_{i}"
        else:
            name = None
        cost_function = MockCostFunction(variables, aux_vars, cost_weight, name=name)
        all_ids.append(cost_function._id)
        all_ids.append(cost_weight._id)
        if name is not None:
            assert name == cost_function.name

    assert len(set(all_ids)) == len(all_ids)
