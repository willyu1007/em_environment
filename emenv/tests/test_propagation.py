import numpy as np

from emenv.api_models import Environment
from emenv.propagation import fspl_dB, propagation_additional_loss_dB, two_ray_flat_loss_dB


def test_fspl_increases_with_distance():
    f = np.array([300.0])
    r_near = np.array([1.0])
    r_far = np.array([10.0])
    assert fspl_dB(f, r_far) > fspl_dB(f, r_near)


def test_total_extra_loss_zero_distance():
    env = Environment()
    f = np.array([[300.0]])
    r = np.array([[0.0]])
    extra = propagation_additional_loss_dB(
        f_MHz=f,
        slant_km=r,
        horizontal_km=r,
        tx_alt_m=np.array([[10.0]]),
        rx_alt_m=np.array([[5.0]]),
        environment=env,
    )
    assert np.allclose(extra, 0.0)


def test_two_ray_far_field_greater_loss():
    f = np.array([[3000.0]])
    horizontal = np.array([[20.0]])  # km
    tx_alt = np.array([[30.0]])
    rx_alt = np.array([[5.0]])
    loss = two_ray_flat_loss_dB(f, horizontal, tx_alt, rx_alt)
    fspl_loss = fspl_dB(f, np.sqrt(horizontal**2 + ((tx_alt - rx_alt) / 1000.0) ** 2))
    assert np.all(loss >= fspl_loss)
