from shapely.ops import split
from shapely.geometry import Polygon, LineString
import numpy as np
import miniball
import math

from players.g2.assigns import *


def sneak(start_pos, end_pos, cake_width, cake_len):
    """
    Given a start position & goal position, uses the 1-pixel shaving technique
    to create a list of necessary steps to get from the start to the goal without
    cutting across the cake.
    """
    nearest_x, x_dist = nearest_edge_x(start_pos, cake_width)
    nearest_y, y_dist = nearest_edge_y(start_pos, cake_len)

    end_x, end_x_dist = nearest_edge_x(end_pos, cake_width)
    end_y, end_y_dist = nearest_edge_y(end_pos, cake_len)

    moves = []

    # if we are on the top or bottom or the board and require more than 1 move
    if y_dist == 0 and (x_dist > 0.1 or nearest_x != end_x):
        bounce_y = bounce(nearest_y)
        moves.append([end_x, bounce_y])

        # if the end is not on the same line so we must ricochet off of corner
        if end_y_dist > 0 or nearest_y != end_y:
            bounce_x = bounce(end_x)
            moves.append([bounce_x, nearest_y])

            # if the end position is on the opposite side
            if end_y_dist == 0:
                bounce_y = bounce(end_y)
                moves.append([bounce_x, end_y])
                moves.append([end_x, bounce_y])

    # if we are on the left or right side of the board and require more than 1 move
    elif x_dist == 0 and (y_dist > 0.1 or nearest_y != end_y):
        bounce_x = bounce(nearest_x)
        moves.append([bounce_x, end_y])

        # if the end is not on the same line so we must ricochet off of corner
        if end_x_dist > 0 or nearest_x != end_x:
            bounce_y = bounce(end_y)
            moves.append([nearest_x, bounce_y])

            # if the end position is on the opposite side
            if end_x_dist == 0:
                bounce_x = bounce(end_x)
                moves.append([end_x, bounce_y])
                moves.append([bounce_x, end_y])

    moves.append(end_pos)
    return moves


def nearest_edge_x(pos, cake_width):
    """
    Returns the nearest X-edge and the distance to said edge
    X-edge is 0 if the position is closer to the left side, or cake_width
        if it is closer to the right side.
    """
    min_x = pos[0]
    x_edge = 0
    if cake_width - pos[0] < min_x:
        min_x = cake_width - pos[0]
        x_edge = cake_width
    return x_edge, min_x


def nearest_edge_y(pos, cake_len):
    """
    Returns the nearest Y-edge and the distance to said edge
    Y-edge is 0 if the position is closer to the top, or cake_len
        if it is closer to the bottom.
    """
    min_y = pos[1]
    y_edge = 0
    if cake_len - pos[1] < min_y:
        min_y = cake_len - pos[1]
        y_edge = cake_len
    return y_edge, min_y


def bounce(margin):
    """
    Returns a value 0.01 away from the provided margin
    """
    if margin == 0:
        return 0.01
    return round(margin - 0.01, 2)


def divide_polygon(polygon: Polygon, from_point, to_point):
    """
    Divide a convex polygon by a line segment into two polygons.

    Parameters:
    - polygon: A convex polygon (as a Shapely Polygon object)
    - line_points: A list containing two points that represent the line segment

    Returns:
    - Two polygons (as shapely Polygon objects) that result from dividing the original polygon
    """

    polygon = polygon.convex_hull
    line = LineString([tuple(from_point), tuple(to_point)])
    # Create the convex polygon and the line segment using Shapely
    # polygon = Polygon(polygon_points)
    # line = LineString(line_points)

    # Check if the line intersects with the polygon
    try:
        if not line.intersects(polygon):
            return [polygon]
        # Split the polygon into two pieces
        result = split(polygon, line)
    except Exception as e:
        # seems to crash when line touches, but doesn't intersec with a polygon
        print(f"Error dividing polygon {polygon} with line {line}")
        return [polygon]

    # Convert the result into individual polygons

    polygons = []
    for i in range(len(result.geoms)):
        # convex_hull always creates valid polygons
        # unlike split()
        polygons.append(result.geoms[i].convex_hull)

    return polygons


def can_cake_fit_in_plate(cake_piece: Polygon, radius=12.5):
    """
    Check if the cake can fit inside a plate of radius 12.5.

    Parameters:
    - cake_pieces: Cake pieces (as shapely Polygon object)
    - radius: The radius of the circle

    Returns:
    - True if the cake can fit inside the plate, False otherwise
    """
    if cake_piece.area < 0.25:
        return True
    # Step 1: Get the points on the cake piece and store as numpy array

    cake_points = np.array(list(zip(*cake_piece.exterior.coords.xy)), dtype=np.double)

    # Step 2: Find the minimum bounding circle of the cake piece
    res = miniball.miniball(cake_points)

    return res["radius"] <= radius


def is_uniform(requests, tolerance=0) -> bool:
    """
    Returns whether or not the requests can be considered uniform
    """
    if len(requests) < 1:
        return True
    return (max(requests) - min(requests)) <= (2 * tolerance)


def divide_requests_evenly(requests):
    """
    If we were to divide the requests into a nearly-square array,
    we return the total sum of every request in the list, a list of
    the sums of all the requests that would be in each row, and a
    list of the sums of all the requests that would be in each column
    """
    n = len(requests)
    s = int(math.sqrt(n))
    requests_copy = requests[:]
    median = (max(requests) + min(requests)) / 2
    if n % s != 0:
        n = s * math.ceil(n / s)
    while len(requests_copy) < n:
        requests_copy.append(median)
    total_sum = 0
    h_sums = []
    v_sums = []
    for i in range(0, len(requests_copy)):
        val = requests_copy[i]
        total_sum += val

        if i < s:
            v_sums.append(val)
        else:
            v_sums[int(i % s)] += val

        if int(i / s) >= len(h_sums):
            h_sums.append(val)
        else:
            h_sums[int(i / s)] += val
    return total_sum, h_sums, v_sums

def penalty_from_split(requests, s, tolerance, cake_len, cake_width):
    """
    
    """
    heights = []
    num_penalty = 0
    i = 0
    total_sum = sum(requests)
    len_adjustment = math.sqrt(total_sum * cake_len / cake_width) / total_sum

    while i < len(requests):
        to_check = requests[i:i+s]

        h_sum = sum(to_check)
        if len(to_check) < s:
            h_sum = s * h_sum / len(to_check)
        height = h_sum * len_adjustment
        heights.append(height)
        if height > 25:
            num_penalty += s*1000
        else:
            min_allowed = max(to_check) - (2 * tolerance)
            num_penalty += sum(i < min_allowed for i in to_check)
        i += s

    widths = []
    k = math.ceil(len(requests) / s)
    width_adjustment = math.sqrt(total_sum * cake_width / cake_len) / total_sum
    for i in range(0,s):
        to_check = requests[i::s]
        v_sum = sum(to_check)
        if len(to_check) < k:
            v_sum = k * v_sum / len(to_check)
        width = v_sum * width_adjustment
        widths.append(width)
        if width > 25:
            num_penalty += k*1000
        else:
            max_poss_height = math.sqrt((25*25)-(width*width))
            if max(heights) > max_poss_height:
                num_penalty += sum(i > max_poss_height for i in heights)
            else:
                min_allowed = max(to_check) - (2 * tolerance)
                num_penalty += sum(i < min_allowed for i in to_check)
    
    return num_penalty, total_sum, heights, widths


def get_best_split(requests, tolerance, cake_width, cake_len):
    """
    """
    n = len(requests)
    s = int(n * 25 / cake_width)
    min_penalty, total_sum, best_heights, best_widths = penalty_from_split(requests, s, tolerance, cake_len, cake_width)
    
    s -= 1
    min_s = max(2, cake_len / 25)
    
    while s >= min_s and min_penalty > 0:
        penalty, sum, h, w = penalty_from_split(requests, s, tolerance, cake_len, cake_width)
        if penalty < min_penalty:
            min_penalty = penalty
            total_sum = sum
            best_heights = h
            best_widths = w
        s -= 1

    return total_sum, best_heights, best_widths

def get_all_uneven_cuts(requests, tolerance, cake_width, cake_len):
    _, heights, widths = get_best_split(requests, tolerance, cake_width, cake_len)
    cuts = []
    # add horizontal cuts
    depth = 0
    for h in heights:
        depth += round(h, 2)
        if depth < cake_len:
            start = [0, depth]
            end = [cake_width, depth]
            cuts.append([start, end])

    # add vertical cuts
    across = 0
    for w in widths:
        across += round(w, 2)
        if across < cake_width:
            start = [across, 0]
            end = [across, cake_len]
            cuts.append([start, end])
    
    return cuts

def grid_enough(requests, width, length, tolerance=0):
    """
    Return whether the requests can be distributed well enough that an uneven
    grid approach is worthwhile.
    """
    total, h_sums, v_sums = divide_requests_evenly(requests)
    h_variance = length * (max(h_sums) - min(h_sums)) / total
    v_variance = width * (max(v_sums) - min(v_sums)) / total
    return min(h_variance, v_variance) <= max(1, tolerance)


def estimate_uneven_penalty(requests, cake_width, cake_len, tolerance=0):
    """
    prob dump this
    """
    _, heights, widths = get_best_split(requests, tolerance,cake_width, cake_len)
    polygon_sizes = []
    polygons = []
    for height in heights:
        for width in widths:
            p = create_polygon(height, width)
            polygons.append(p)
            # polygon_sizes.append(round(p.area, 2))
    # print("POLYGON SIZES =", sorted(polygon_sizes))
    print("NUM POLYGONS =", len(polygons))
    assignment = greedy_best_fit_assignment(polygons, requests, tolerance)
    return calculate_total_penalty(assignment, polygons, requests, tolerance)


def create_polygon(width, height):
    """Creates a polygon representing a rectangle given its width and height."""

    # Define the coordinates of the rectangle's corners
    coordinates = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]

    # Create the polygon using the coordinates
    polygon = Polygon(coordinates)

    return polygon
