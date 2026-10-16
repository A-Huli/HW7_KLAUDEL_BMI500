"""Curve shapes and a generic least-squares fitter (BMI 500, HW 3, Part A).

Holds only the reusable parts: the three model functions from the homework
and the CurveModel / FittedCurve pair. The fitting workflow, model
definitions and plots live in the notebook.
"""

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import curve_fit


# ---------------------------------------------------------------------------
# Model shapes
# ---------------------------------------------------------------------------
def quadratic(x: NDArray[np.float64], c1: float, c2: float, c3: float) -> NDArray[np.float64]:
    """Quadratic age trend, y = c1*x^2 + c2*x + c3.

    Args:
        x (NDArray): Age in years.
        c1 (float): Curvature term in mmHg per year^2.
        c2 (float): Linear slope in mmHg per year.
        c3 (float): Intercept, the modelled value at age 0, in mmHg.

    Returns:
        NDArray: Blood pressure in mmHg at each age in x.
    """
    return c1 * x**2 + c2 * x + c3


def sigmoid(x: NDArray[np.float64], S0: float, dS: float, k: float, a0: float) -> NDArray[np.float64]:
    """Sigmoid rise with a baseline, y = S0 + dS / (1 + exp(-k*(x - a0))).

    Args:
        x (NDArray): Age in years.
        S0 (float): Baseline value at young ages, in mmHg.
        dS (float): Total rise from baseline to the upper plateau, in mmHg.
        k (float): Steepness of the rise, in 1/years.
        a0 (float): Age at half of the rise, in years.

    Returns:
        NDArray: Blood pressure in mmHg at each age in x.
    """
    return S0 + dS / (1 + np.exp(-k * (x - a0)))


def gaussian(x: NDArray[np.float64], D0: float, dD: float, a_peak: float, sigma: float) -> NDArray[np.float64]:
    """Gaussian hump with a baseline, y = D0 + dD * exp(-(x - a_peak)^2 / (2*sigma^2)).

    Args:
        x (NDArray): Age in years.
        D0 (float): Baseline value far from the peak, in mmHg.
        dD (float): Height of the peak above baseline, in mmHg.
        a_peak (float): Age at which the peak occurs, in years.
        sigma (float): Width of the peak (standard deviation), in years.

    Returns:
        NDArray: Blood pressure in mmHg at each age in x.
    """
    return D0 + dD * np.exp(-((x - a_peak) ** 2) / (2 * sigma**2))


# ---------------------------------------------------------------------------
# Generic fitting
# ---------------------------------------------------------------------------
class CurveModel:
    """A curve shape y = f(x, *params) and the settings needed to fit it.

    The object is a description only. It stores no fit results, so one
    instance can be fitted to many datasets.

    Attributes:
        name (str): Short label used in printouts and plot legends.
        f (Callable): Model function with signature f(x, *params).
        param_names (list[str]): Names of the parameters, in the order f expects them.
        p0 (list[float]): Starting values for the optimiser.
        bounds (tuple): (lower, upper) bounds per parameter, as scipy.optimize.curve_fit
            expects. Defaults to unbounded.
    """

    def __init__(
        self,
        name: str,
        f: Callable[..., NDArray[np.float64]],
        param_names: Sequence[str],
        p0: Sequence[float],
        bounds: tuple = (-np.inf, np.inf),
    ) -> None:
        """Store the model shape and its fitting settings.

        Args:
            name (str): Short label for the model.
            f (Callable): Model function f(x, *params).
            param_names (Sequence[str]): Parameter names in the order f expects them.
            p0 (Sequence[float]): Starting values for the optimiser, one per parameter.
            bounds (tuple, optional): (lower, upper) bounds per parameter. Defaults to unbounded.

        Raises:
            ValueError: If p0 and param_names have different lengths.
        """
        if len(p0) != len(param_names):
            raise ValueError("p0 and param_names must have the same length")
        self.name = name
        self.f = f
        self.param_names = list(param_names)
        self.p0 = list(p0)
        self.bounds = bounds

    def fit(self, x: ArrayLike, y: ArrayLike) -> "FittedCurve":
        """Fit the model to data by least squares.

        For a model that is linear in its parameters (the quadratic) the
        least-squares problem has a single minimum and the optimiser returns
        the closed-form solution. For the sigmoid and Gaussian the result can
        depend on p0 and bounds.

        Args:
            x (ArrayLike): Independent variable, here age in years.
            y (ArrayLike): Observed values, here mean blood pressure in mmHg.

        Returns:
            FittedCurve: A new object holding this model and the fitted parameters.

        Raises:
            RuntimeError: If scipy's optimiser does not converge.
        """
        params, _ = curve_fit(self.f, x, y, p0=self.p0, bounds=self.bounds, maxfev=20000)
        return FittedCurve(self, params)


@dataclass
class FittedCurve:
    """The result of fitting one CurveModel to one dataset.

    Attributes:
        model (CurveModel): The shape that was fitted.
        params (NDArray): Fitted parameter values, in model.param_names order.
    """

    model: CurveModel
    params: NDArray[np.float64]

    def predict(self, x: ArrayLike) -> NDArray[np.float64]:
        """Evaluate the fitted curve.

        Args:
            x (ArrayLike): Ages in years at which to evaluate the curve.

        Returns:
            NDArray: Predicted blood pressure in mmHg at each x.
        """
        return self.model.f(np.asarray(x, dtype=float), *self.params)

    @property
    def name(self) -> str:
        """str: Label of the underlying model."""
        return self.model.name

    @property
    def n_params(self) -> int:
        """int: Number of fitted parameters, needed for AIC and BIC."""
        return len(self.params)

    def __repr__(self) -> str:
        """Return the model name with each parameter and its value."""
        pairs = ", ".join(f"{n}={v:.4g}" for n, v in zip(self.model.param_names, self.params))
        return f"{self.name}({pairs})"