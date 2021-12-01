import collections
from typing import Dict, List, Optional, Tuple, cast

import numpy as np
import torch
import torch.nn as nn

import theseus as th


class TactileMeasModel(nn.Module):
    def __init__(self, input_size: int, output_size: int):
        super().__init__()

        self.fc1 = nn.Linear(input_size, output_size)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor, k: torch.Tensor):
        x = torch.cat([x1, x2], dim=1)

        k1_ = k.unsqueeze(1)  # b x 1 x cl
        x1_ = x.unsqueeze(-1)  # b x dim x 1
        x = torch.mul(x1_, k1_)  # b x dim x cl

        x = x.view(x.shape[0], -1)
        x = self.fc1(x)

        return x


def init_tactile_model_from_file(model: nn.Module, filename: str):

    model_saved = torch.jit.load(filename)
    state_dict_saved = model_saved.state_dict()
    state_dict_new = collections.OrderedDict()
    state_dict_new["fc1.weight"] = state_dict_saved["model.fc1.weight"]
    state_dict_new["fc1.bias"] = state_dict_saved["model.fc1.bias"]

    model.load_state_dict(state_dict_new)

    return model


# Set some parameters for the cost weights
class TactileWeightModel(nn.Module):
    def __init__(
        self, device: str, dim: int = 3, wt_init: Optional[torch.Tensor] = None
    ):
        super().__init__()

        wt_init_ = torch.rand(1, dim)
        if wt_init is not None:
            wt_init_ = wt_init
        self.param = nn.Parameter(wt_init_.to(device))

    def forward(self):
        return self.param.clone()


# ----------------------------------------------------------------------------------- #
# ------------------------------- Theseus Model Interface --------------------------- #
# ----------------------------------------------------------------------------------- #


def get_tactile_nn_measurements_inputs(
    batch: Tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    device: str,
    class_label: int,
    num_classes: int,
    min_win_mf: int,
    max_win_mf: int,
    step_win_mf: int,
    time_steps: int,
    model: Optional[nn.Module] = None,
):
    inputs = {}

    if model is not None:
        images_feat_meas = batch[0].to(device)
        class_label_vec = (
            nn.functional.one_hot(torch.tensor(class_label), torch.tensor(num_classes))
            .view(1, -1)
            .to(device)
        )

        meas_model_input_1_list: List[torch.Tensor] = []
        meas_model_input_2_list: List[torch.Tensor] = []
        for i in range(min_win_mf, time_steps):
            for offset in range(min_win_mf, np.minimum(i, max_win_mf), step_win_mf):
                meas_model_input_1_list.append(images_feat_meas[:, i - offset, :])
                meas_model_input_2_list.append(images_feat_meas[:, i, :])

        meas_model_input_1 = torch.cat(meas_model_input_1_list, dim=0)
        meas_model_input_2 = torch.cat(meas_model_input_2_list, dim=0)
        num_measurements = meas_model_input_1.shape[0]
        model_measurements = model.forward(
            meas_model_input_1, meas_model_input_2, class_label_vec
        ).reshape(
            -1, num_measurements, 4
        )  # data format (x, y, cos, sin)
    else:  # use oracle model
        model_measurements = []
        for i in range(min_win_mf, time_steps):
            for offset in range(min_win_mf, np.minimum(i, max_win_mf), step_win_mf):
                eff_pose_1 = th.SE2(x_y_theta=batch[1][:, i - offset])
                obj_pose_1 = th.SE2(x_y_theta=batch[2][:, i - offset])
                eff_pose_1__obj = obj_pose_1.between(eff_pose_1)

                eff_pose_2 = th.SE2(x_y_theta=batch[1][:, i])
                obj_pose_2 = th.SE2(x_y_theta=batch[2][:, i])
                eff_pose_2__obj = obj_pose_2.between(eff_pose_2)

                meas_pose_rel = cast(th.SE2, eff_pose_1__obj.between(eff_pose_2__obj))
                model_measurements.append(
                    torch.cat(
                        (
                            meas_pose_rel.xy(),
                            meas_pose_rel.theta().cos(),
                            meas_pose_rel.theta().sin(),
                        ),
                        dim=1,
                    )
                )  # data format (x, y, cos, sin)

        num_measurements = len(model_measurements)
        model_measurements = torch.cat(model_measurements, dim=0).reshape(
            -1, num_measurements, 4
        )
        model_measurements = model_measurements.to(device)

    # set MovingFrameBetween measurements from the NN output
    nn_meas_idx = 0
    for i in range(min_win_mf, time_steps):
        for offset in range(min_win_mf, np.minimum(i, max_win_mf), step_win_mf):
            meas_xycs_ = torch.stack(
                [
                    model_measurements[:, nn_meas_idx, 0],
                    model_measurements[:, nn_meas_idx, 1],
                    model_measurements[:, nn_meas_idx, 2],
                    model_measurements[:, nn_meas_idx, 3],
                ],
                dim=1,
            )
            inputs[f"nn_measurement_{i-offset}_{i}"] = meas_xycs_
            nn_meas_idx = nn_meas_idx + 1

    return inputs


def get_tactile_motion_capture_inputs(
    batch: Tuple[torch.Tensor, torch.Tensor, torch.Tensor], device: str, time_steps: int
):
    inputs = {}
    captures = batch[1].to(device)
    for step in range(time_steps):
        capture = captures[:, step, :]
        cature_xycs = torch.stack(
            [capture[:, 0], capture[:, 1], capture[:, 2].cos(), capture[:, 2].sin()],
            dim=1,
        )
        inputs[f"motion_capture_{step}"] = cature_xycs
    return inputs


def get_tactile_cost_weight_inputs(qsp_model, mf_between_model):
    return {"qsp_weight": qsp_model(), "mf_between_weight": mf_between_model()}


def get_tactile_initial_optim_vars(
    batch: Tuple[torch.Tensor, torch.Tensor, torch.Tensor], device: str, time_steps: int
):
    inputs_ = {}
    eff_captures_ = batch[1].to(device)
    obj_captures_ = batch[2].to(device)

    for step in range(time_steps):
        eff_xyth_ = eff_captures_[:, step, :]
        eff_xycs_ = torch.stack(
            [
                eff_xyth_[:, 0],
                eff_xyth_[:, 1],
                eff_xyth_[:, 2].cos(),
                eff_xyth_[:, 2].sin(),
            ],
            dim=1,
        )

        obj_xyth_ = obj_captures_[:, step, :]
        obj_xycs_ = torch.stack(
            [
                obj_xyth_[:, 0],
                obj_xyth_[:, 1],
                obj_xyth_[:, 2].cos(),
                obj_xyth_[:, 2].sin(),
            ],
            dim=1,
        )

        # layer will route this to the optimization variables with the given name
        inputs_[f"obj_pose_{step}"] = obj_xycs_.clone() + 0.0 * torch.cat(
            [torch.randn((1, 2)), torch.zeros((1, 2))], dim=1
        ).to(device)
        inputs_[f"eff_pose_{step}"] = eff_xycs_.clone()

    return inputs_


def get_tactile_poses_from_values(
    batch_size: int,
    values: Dict[str, torch.Tensor],
    time_steps,
    device: str,
    key: str = "pose",
):
    poses = torch.empty(batch_size, time_steps, 3, device=device)
    for t_ in range(time_steps):
        poses[:, t_, :2] = values[f"{key}_{t_}"][:, 0:2]
        poses[:, t_, 2] = torch.atan2(
            values[f"{key}_{t_}"][:, 3], values[f"{key}_{t_}"][:, 2]
        )
    return poses
