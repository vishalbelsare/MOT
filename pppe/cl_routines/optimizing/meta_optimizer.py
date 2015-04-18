from ...cl_environments import CLEnvironment
from ...cl_routines.sampling.metropolis_hastings import MetropolisHastings
from ...cl_routines.smoothing.median import MedianSmoother
from ...cl_routines.optimizing.base import AbstractOptimizer
from ...cl_routines.mapping.error_measures import ErrorMeasures
from ...cl_routines.mapping.residual_calculator import ResidualCalculator
from ...cl_routines.optimizing.gridsearch import GridSearch
from ...cl_routines.optimizing.nmsimplex import NMSimplex
from ...models.interfaces import SmoothableModelInterface

__author__ = 'Robbert Harms'
__date__ = "2014-06-19"
__license__ = "LGPL v3"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


class MetaOptimizer(AbstractOptimizer):

    def __init__(self, cl_environments=None, load_balancer=None, use_param_codec=True, patience=None):
        """This meta optimization routine uses optimizers, and samplers to provide a meta optimization.

        In general one can enable a grid search beforehand, optimization, sampling and optionally calculating extra
        error maps.

        Args:
            cl_environments (list of CLEnvironment): a list with the cl environments to use
            load_balancer (LoadBalancer): the load balance strategy to use
            use_param_codec (boolean): if this minimization should use the parameter codecs (param transformations)
            patience (int): The patience is used in the calculation of how many iterations to iterate the optimizer.
                The exact semantical value of this parameter may change per optimizer.

        Attributes:
            enable_grid_search (boolean, default False); If we want to enable a grid search before optimization
            enable_sampling (boolean, default False): If we want to enable sampling
            enable_error_maps (boolean, default True): If we want to calculate various error maps at the end
            extra_optim_runs (boolean, default 1): The amount of extra optimization runs with a smoothing step
                in between.
            extra_optim_runs_optimizers (list, default None): A list of optimizers with one optimizer for every extra
                optimization run. If the length of this list is smaller than the number of runs, the last optimizer is
                used for all remaining runs.
            extra_optim_runs_smoothers (list, default None): A list of smoothers with one smoother for every extra
                optimization run. If the length of this list is smaller than the number of runs, the last smoother is
                used for all remaining runs.
            grid_search (Optimizer, default GridSearch): The grid search optimizer.
            optimizer (Optimizer, default NMSimplex): The default optimization routine
            smoother (Smoother, default MedianSmoother(1)): The default smoothing routine
            sampler (Sampler, default MetropolisHastings): The default sampling routine.
        """
        super(MetaOptimizer, self).__init__(cl_environments, load_balancer, use_param_codec)
        self.enable_grid_search = False
        self.enable_sampling = False
        self.enable_error_maps = True

        self.extra_optim_runs = 1
        self.extra_optim_runs_optimizers = None
        self.extra_optim_runs_smoothers = None

        self.grid_search = GridSearch(cl_environments=self.cl_environments, load_balancer=self.load_balancer,
                                      use_param_codec=self.use_param_codec)
        self.optimizer = NMSimplex(cl_environments=self.cl_environments, load_balancer=self.load_balancer,
                                   use_param_codec=self.use_param_codec)
        self.smoother = MedianSmoother((1, 1, 1))
        self.sampler = MetropolisHastings()

    def minimize(self, model, init_params=None, full_output=False):
        results = init_params

        if self.enable_grid_search:
            results = self.grid_search.minimize(model, init_params=results)

        results = self.optimizer.minimize(model, init_params=results)

        if self.extra_optim_runs and isinstance(model, SmoothableModelInterface):
            for i in range(self.extra_optim_runs):
                optimizer = self.optimizer
                smoother = self.smoother

                if self.extra_optim_runs_optimizers and i < len(self.extra_optim_runs_optimizers):
                    optimizer = self.extra_optim_runs_optimizers[i]

                if self.extra_optim_runs_smoothers and i < len(self.extra_optim_runs_smoothers):
                    smoother = self.extra_optim_runs_smoothers[i]

                smoothed_maps = model.smooth(results, smoother)
                results = optimizer.minimize(model, init_params=smoothed_maps)

        samples = ()
        other_output = {}
        if self.enable_sampling:
            samples, other_output = self.sampler.sample(model, init_params=results, full_output=True)
            results.update(model.samples_to_statistics(samples))

            nmr_voxels = samples[samples.keys()[0]].shape[0]
            for key, value in other_output.items():
                if value.shape[0] == nmr_voxels:
                    results.update({'sampling.' + key: value})

        if self.enable_error_maps:
            errors = ResidualCalculator().calculate(model, results)
            error_measures = ErrorMeasures().calculate(errors)
            results.update(error_measures)

        if full_output:
            d = {}
            if self.enable_sampling:
                d.update({'samples': samples})
                d.update(other_output)
            return results, d
        return results

    @property
    def cl_environments(self):
        return self._cl_environments

    @cl_environments.setter
    def cl_environments(self, cl_environments):
        if isinstance(cl_environments, CLEnvironment):
            cl_environments = [cl_environments]

        self.optimizer.cl_environments = cl_environments
        self.grid_search.cl_environments = cl_environments
        self.smoother.cl_environments = cl_environments
        self.sampler.cl_environments = cl_environments

        self._cl_environments = cl_environments

    @property
    def load_balancer(self):
        return self._load_balancer

    @load_balancer.setter
    def load_balancer(self, load_balancer):

        self.optimizer.load_balancer = load_balancer
        self.grid_search.load_balancer = load_balancer
        self.smoother.load_balancer = load_balancer
        self.sampler.load_balancer = load_balancer

        self._load_balancer = load_balancer