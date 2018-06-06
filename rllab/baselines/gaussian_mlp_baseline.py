import numpy as np

from rllab.core import Serializable
from rllab.core import Parameterized
from rllab.baselines import Baseline
from rllab.misc.overrides import overrides
from rllab.regressors.gaussian_mlp_regressor import GaussianMLPRegressor


class GaussianMLPBaseline(Baseline, Parameterized):

    def __init__(
            self,
            env_spec,
            subsample_factor=1.,
            num_seq_inputs=1,
            regressor_args=None,
    ):
        Serializable.quick_init(self, locals())
        super(GaussianMLPBaseline, self).__init__(env_spec)
        if regressor_args is None:
            regressor_args = dict()

        obs_dim = env_spec.observation_space.n if \
                isinstance(env_spec.observation_space, gym.spaces.Discrete) \
                else np.prod(env_spec.observation_space.shape)

        self._regressor = GaussianMLPRegressor(
            input_shape=(obs_dim * num_seq_inputs,),
            output_dim=1,
            name="vf",
            **regressor_args
        )

    @overrides
    def fit(self, paths):
        observations = np.concatenate([p["observations"] for p in paths])
        returns = np.concatenate([p["returns"] for p in paths])
        self._regressor.fit(observations, returns.reshape((-1, 1)))

    @overrides
    def predict(self, path):
        return self._regressor.predict(path["observations"]).flatten()

    @overrides
    def get_param_values(self, **tags):
        return self._regressor.get_param_values(**tags)

    @overrides
    def set_param_values(self, flattened_params, **tags):
        self._regressor.set_param_values(flattened_params, **tags)
