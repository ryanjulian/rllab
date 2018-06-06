import gym
import numpy as np
import lasagne.nonlinearities as NL

import lasagne.layers as L
from rllab.core import ConvNetwork
from rllab.core import LasagnePowered
from rllab.core import Serializable
from rllab.distributions import Categorical
from rllab.policies import StochasticPolicy
from rllab.misc import ext
from rllab.misc import logger
from rllab.misc import special
from rllab.misc import tensor_utils
from rllab.misc.overrides import overrides


class CategoricalConvPolicy(StochasticPolicy, LasagnePowered):
    def __init__(
            self,
            name,
            env_spec,
            conv_filters, conv_filter_sizes, conv_strides, conv_pads,
            hidden_sizes=[],
            hidden_nonlinearity=NL.rectify,
            output_nonlinearity=NL.softmax,
            prob_network=None,
    ):
        """
        :param env_spec: A spec for the mdp.
        :param hidden_sizes: list of sizes for the fully connected hidden layers
        :param hidden_nonlinearity: nonlinearity used for each hidden layer
        :param prob_network: manually specified network for this policy, other network params
        are ignored
        :return:
        """
        Serializable.quick_init(self, locals())

        assert isinstance(env_spec.action_space, gym.spaces.Discrete)

        self._env_spec = env_spec

        if prob_network is None:
            prob_network = ConvNetwork(
                input_shape=env_spec.observation_space.shape,
                output_dim=env_spec.action_space.n,
                conv_filters=conv_filters,
                conv_filter_sizes=conv_filter_sizes,
                conv_strides=conv_strides,
                conv_pads=conv_pads,
                hidden_sizes=hidden_sizes,
                hidden_nonlinearity=hidden_nonlinearity,
                output_nonlinearity=NL.softmax,
                name="prob_network",
            )

        self._l_prob = prob_network.output_layer
        self._l_obs = prob_network.input_layer
        self._f_prob = ext.compile_function(
            [prob_network.input_layer.input_var],
            L.get_output(prob_network.output_layer)
        )

        self._dist = Categorical(env_spec.action_space.n)

        super(CategoricalConvPolicy, self).__init__(env_spec)
        LasagnePowered.__init__(self, [prob_network.output_layer])

    @property
    def vectorized(self):
        return True

    @overrides
    def dist_info_sym(self, obs_var, state_info_vars=None):
        return dict(
            prob=L.get_output(
                self._l_prob,
                {self._l_obs: obs_var}
            )
        )

    @overrides
    def dist_info(self, obs, state_infos=None):
        return dict(prob=self._f_prob(obs))

    # The return value is a pair. The first item is a matrix (N, A), where each
    # entry corresponds to the action value taken. The second item is a vector
    # of length N, where each entry is the density value for that action, under
    # the current policy
    @overrides
    def get_action(self, observation):
        flat_obs = special.to_onehot(observation, self.observation_space.n) \
        if isinstance(self.observation_space, gym.spaces.Discrete) else np.asarray(observation).flatten()

        prob = self._f_prob([flat_obs])[0]
        action = self.action_space.weighted_sample(prob)
        return action, dict(prob=prob)

    def get_actions(self, observations):
        flat_obs = None
        if isinstance(self.observation_space, gym.spaces.Discrete):
            flat_obs = special.to_onehot_n(observations, self.observation_space.n)
        else:
            observations = np.asarray(observations)
            flat_obs = observations.reshape((observations.shape[0], -1))

        probs = self._f_prob(flat_obs)
        actions = list(map(self.action_space.weighted_sample, probs))
        return actions, dict(prob=probs)

    @property
    def distribution(self):
        return self._dist
