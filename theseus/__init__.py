# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
__version__ = "0.1.1"


from .core import (  # usort: skip
    as_variable,
    AutoDiffCostFunction,
    AutogradMode,
    CostFunction,
    CostWeight,
    DiagonalCostWeight,
    HuberLoss,
    Objective,
    RobustCostFunction,
    RobustLoss,
    ScaleCostWeight,
    Variable,
    Vectorize,
    WelschLoss,
)
from .geometry import (  # usort: skip
    adjoint,
    between,
    compose,
    enable_lie_tangent,
    exp_map,
    inverse,
    LieGroup,
    LieGroupTensor,
    local,
    log_map,
    Manifold,
    no_lie_tangent,
    Point2,
    Point3,
    rand_point2,
    rand_point3,
    rand_se2,
    rand_se3,
    rand_so2,
    rand_so3,
    rand_vector,
    randn_point2,
    randn_point3,
    randn_se2,
    randn_se3,
    randn_so2,
    randn_so3,
    randn_vector,
    retract,
    SE2,
    SE3,
    set_lie_tangent_enabled,
    SO2,
    SO3,
    Vector,
)
from .optimizer import (  # usort: skip
    DenseLinearization,
    local_gaussian,
    ManifoldGaussian,
    OptimizerInfo,
    retract_gaussian,
    SparseLinearization,
    VariableOrdering,
)
from .optimizer.linear import (  # usort: skip
    CholeskyDenseSolver,
    CholmodSparseSolver,
    DenseSolver,
    LinearOptimizer,
    LUCudaSparseSolver,
    LUDenseSolver,
)
from .optimizer.nonlinear import (  # usort: skip
    BackwardMode,
    GaussNewton,
    LevenbergMarquardt,
    NonlinearLeastSquares,
    NonlinearOptimizerInfo,
    NonlinearOptimizerParams,
    NonlinearOptimizerStatus,
)
from .theseus_layer import TheseusLayer  # usort: skip

import theseus.embodied as eb  # usort: skip

# Aliases for some standard cost functions
Difference = eb.Local
Between = eb.Between
Local = eb.Local
