"""
Lhs functions are inspired by
https://github.com/clicumu/pyDOE2/blob/
master/pyDOE2/doe_lhs.py
"""
import numpy as np
from sklearn.utils import check_random_state
from scipy import spatial
from ..utils import random_permute_matrix
from ..space import Space, Categorical
from .base import InitialPointGenerator


class Lhs(InitialPointGenerator):
    """Latin hypercube sampling

    Parameters
    ----------
    lhs_type : str, default='classic'
        - 'classic' - a small random number is added
        - 'centered' - points are set uniformly in each interval

    criterion : str or None, default='maximin'
        When set to None, the LHS is not optimized

        - 'correlation' : optimized LHS by minimizing the correlation
        - 'maximin' : optimized LHS by maximizing the minimal pdist
        - 'ratio' : optimized LHS by minimizing the ratio
          `max(pdist) / min(pdist)`

    iterations : int
        Defines the number of iterations for optimizing LHS
    """
    def __init__(self, lhs_type="classic", criterion="maximin",
                 iterations=1000):
        self.lhs_type = lhs_type
        self.criterion = criterion
        self.iterations = iterations

    def generate(self, dimensions, n_samples, random_state=None):
        """Creates latin hypercube samples.

        Parameters
        ----------
        dimensions : list, shape (n_dims,)
            List of search space dimensions.
            Each search dimension can be defined either as

            - a `(lower_bound, upper_bound)` tuple (for `Real` or `Integer`
              dimensions),
            - a `(lower_bound, upper_bound, "prior")` tuple (for `Real`
              dimensions),
            - as a list of categories (for `Categorical` dimensions), or
            - an instance of a `Dimension` object (`Real`, `Integer` or
              `Categorical`).

        n_samples : int
            The order of the LHS sequence. Defines the number of samples.
        random_state : int, RandomState instance, or None (default)
            Set random state to something other than None for reproducible
            results.

        Returns
        -------
        np.array, shape=(n_dim, n_samples)
            LHS set
        """
        rng = check_random_state(random_state)
        space = Space(dimensions)
        transformer = space.get_transformer()
        if space.is_partly_categorical:
            space.set_transformer("identity")
            space.set_transformer_by_type("label", Categorical)
            trans_cat_int = space.get_transformer()
        n_dim = space.n_dims
        space.set_transformer("normalize")
        trans_normalize = space.get_transformer()
        if self.criterion is None or n_samples == 1:
            h = self._lhs_normalized(n_dim, n_samples, random_state)
            h = space.inverse_transform(h)
            space.set_transformer(transformer)
            return h
        else:
            h_opt = self._lhs_normalized(n_dim, n_samples, random_state)
            space.set_transformer(trans_normalize)
            h_opt = space.inverse_transform(h_opt)

            if self.criterion == "correlation":
                mincorr = np.inf
                for i in range(self.iterations):
                    # Generate a random LHS
                    h = self._lhs_normalized(n_dim, n_samples, random_state)
                    space.set_transformer(trans_normalize)
                    h = space.inverse_transform(h)
                    if space.is_partly_categorical:
                        space.set_transformer(trans_cat_int)
                        h = space.transform(h)
                    r = np.corrcoef(np.array(h).T)
                    if np.max(np.abs(r[r != 1])) < mincorr:
                        mincorr = np.max(np.abs(r - np.eye(r.shape[0])))
                        h_opt = h.copy()
                        if space.is_partly_categorical:
                            space.set_transformer(trans_cat_int)
                            h_opt = space.inverse_transform(h_opt)

            elif self.criterion == "maximin":
                maxdist = 0
                # Maximize the minimum distance between points
                for i in range(self.iterations):
                    h = self._lhs_normalized(n_dim, n_samples, random_state)
                    space.set_transformer(trans_normalize)
                    h = space.inverse_transform(h)
                    if space.is_partly_categorical:
                        space.set_transformer(trans_cat_int)
                        h = space.transform(h)
                    d = spatial.distance.pdist(np.array(h), 'euclidean')
                    if maxdist > np.min(d):
                        maxdist = np.min(d)
                        h_opt = h.copy()
                        if space.is_partly_categorical:
                            space.set_transformer(trans_cat_int)
                            h_opt = space.inverse_transform(h_opt)
            elif self.criterion == "ratio":
                minratio = np.inf

                # Maximize the minimum distance between points
                for i in range(self.iterations):
                    h = self._lhs_normalized(n_dim, n_samples, random_state)
                    space.set_transformer(trans_normalize)
                    h = space.inverse_transform(h)
                    if space.is_partly_categorical:
                        space.set_transformer(trans_cat_int)
                        h = space.transform(h)
                    p = spatial.distance.pdist(np.array(h), 'euclidean')
                    ratio = np.max(p) / np.min(p)
                    if minratio < ratio:
                        minratio = ratio
                        h_opt = h.copy()
                        if space.is_partly_categorical:
                            space.set_transformer(trans_cat_int)
                            h_opt = space.inverse_transform(h_opt)
            else:
                raise ValueError("Wrong criterion."
                                 "Got {}".format(self.criterion))
            space.set_transformer(transformer)
            return h_opt

    def _lhs_normalized(self, n_dim, n_samples, random_state):
        rng = check_random_state(random_state)
        x = np.linspace(0, 1, n_samples + 1)
        u = rng.rand(n_samples, n_dim)
        h = np.zeros_like(u)
        if self.lhs_type == "centered":
            for j in range(n_dim):
                h[:, j] = np.diff(x) / 2.0 + x[:n_samples]
        elif self.lhs_type == "classic":
            for j in range(n_dim):
                h[:, j] = u[:, j] * np.diff(x) + x[:n_samples]
        else:
            raise ValueError("Wrong lhs_type. Got ".format(self.lhs_type))
        return random_permute_matrix(h, random_state=random_state)
