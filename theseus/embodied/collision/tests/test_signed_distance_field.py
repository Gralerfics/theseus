# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import pytest  # noqa
import torch

import theseus as th
from theseus.utils import numeric_jacobian


def test_sdf_2d_shapes():
    generator = torch.Generator()
    generator.manual_seed(0)
    for batch_size in [1, 10, 100]:
        for field_width in [1, 10, 100]:
            for field_height in [1, 10, 100]:
                for num_points in [1, 10, 100]:
                    origin = torch.randn(batch_size, 2)
                    sdf_data = torch.randn(batch_size, field_width, field_height)
                    points = torch.randn(batch_size, 2, num_points)
                    cell_size = torch.randn(batch_size, 1)
                    sdf = th.eb.SignedDistanceField2D(origin, cell_size, sdf_data)
                    dist, jac = sdf.signed_distance(points)
                    assert dist.shape == (batch_size, num_points)
                    assert jac.shape == (batch_size, num_points, 2)


def test_signed_distance_2d():
    data = torch.tensor(
        [
            [1.7321, 1.4142, 1.4142, 1.4142, 1.7321],
            [1.4142, 1, 1, 1, 1.4142],
            [1.4142, 1, 1, 1, 1.4142],
            [1.4142, 1, 1, 1, 1.4142],
            [1.7321, 1.4142, 1.4142, 1.4142, 1.7321],
        ]
    ).view(1, 5, 5)
    sdf = th.eb.SignedDistanceField2D(
        -0.2 * torch.ones(1, 2), 0.1 * torch.ones(1, 1), data
    )

    points = torch.tensor([[0, 0], [0.18, -0.17]])
    rows, cols, _ = sdf.convert_points_to_cell(points)
    assert torch.allclose(rows, torch.tensor([[2.0, 0.3]]))
    assert torch.allclose(cols, torch.tensor([[2.0, 3.8]]))

    dist, _ = sdf.signed_distance(points)
    assert torch.allclose(dist, torch.tensor([1.0, 1.567372]).view(1, 2))


def test_sdf_2d_creation():
    map1 = torch.tensor(
        [
            [0, 1, 1, 1, 1],
            [0, 0, 1, 1, 1],
            [0, 1, 1, 1, 1],
            [0, 1, 1, 1, 0],
            [0, 1, 1, 0, 0],
        ]
    )
    map2 = torch.zeros(5, 5)
    data_maps = th.Variable(torch.stack([map1, map2]))
    sdf_batch = th.eb.SignedDistanceField2D(
        -0.2 * torch.ones(2, 2), 0.1 * torch.ones(2, 1), occupancy_map=data_maps
    )
    # generate verification data for map1
    import numpy as np

    s2, s5 = np.sqrt(2), np.sqrt(5)
    sdf_map1_verify = 0.1 * torch.tensor(
        [
            [1, -1, -s2, -s5, -3],
            [s2, 1, -1, -2, -2],
            [1, -1, -s2, -s2, -1],
            [1, -1, -s2, -1, 1],
            [1, -1, -1, 1, s2],
        ]
    )
    if sdf_batch.sdf_data.data.dtype == torch.float32:
        sdf_map1_verify = sdf_map1_verify.float()
    assert torch.allclose(
        sdf_batch.sdf_data[0], sdf_map1_verify
    ), "Failed conversion of map with obstacle."
    assert torch.allclose(
        sdf_batch.sdf_data[1], torch.tensor(1.0)
    ), "Failed conversion of map with no obstacle."


def test_signed_distance_2d_jacobian():
    for batch_size in [1, 10, 100]:
        origin = th.Variable(torch.randn(batch_size, 2).double())
        sdf_data = th.Variable(torch.randn(batch_size, 10, 10).double())
        cell_size = th.Variable(torch.rand(batch_size, 1).double())
        sdf = th.eb.SignedDistanceField2D(origin, cell_size, sdf_data)
        for num_points in [1, 10]:
            points = torch.randn(batch_size, 2, num_points).double()
            _, jacobian = sdf.signed_distance(points)

            for p_index in range(num_points):
                x = th.Vector(data=points[:, :1, p_index].double())
                y = th.Vector(data=points[:, 1:, p_index].double())

                def new_distance_fn(vars):
                    new_points = torch.stack([vars[0].data, vars[1].data], dim=1)
                    new_dist = sdf.signed_distance(new_points)[0]
                    return th.Vector(data=new_dist)

                expected_jacs = numeric_jacobian(
                    new_distance_fn, [x, y], function_dim=1, delta_mag=1e-7
                )
                expected_jacobian = torch.cat(expected_jacs, dim=2).squeeze(1)
                # This makes failures more explicit than torch.allclose()
                diff = (expected_jacobian - jacobian[:, p_index]).norm(p=float("inf"))
                assert diff < 1e-5
