"""Independent fill-area checks from actual marker paths and display transforms."""
import numpy as np


def path_fill_area(path):
    """Integrate x dy - y dx exactly along the path's polynomial segments."""
    area = 0.
    for curve, _ in path.iter_bezier():
        coefficients = curve.polynomial_coefficients
        if len(coefficients) < 2:
            continue
        x, y = coefficients[:, 0], coefficients[:, 1]
        powers = np.arange(1, len(coefficients))
        integral = np.convolve(x, y[1:] * powers) - np.convolve(y, x[1:] * powers)
        area += np.sum(integral / (np.arange(len(integral)) + 1)) / 2
    return abs(float(area))


def collection_fill_areas_pt2(collection, figure):
    """Measure rendered fills, excluding stroke; offsets do not change area."""
    figure.canvas.draw()
    paths = collection.get_paths()
    transforms = collection.get_transforms()
    return np.array([path_fill_area(paths[index % len(paths)])
                     * abs(np.linalg.det(transform[:2, :2])) * (72 / figure.dpi) ** 2
                     for index, transform in enumerate(transforms)])
