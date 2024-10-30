from typing import List, Callable
import numpy as np
import logging
import constants
import miniball
from enum import Enum
from shapely.geometry import Polygon

from piece_of_cake_state import PieceOfCakeState
from players.g2.helpers import *
from players.g2.even_cuts import *
from players.g2.assigns import sorted_assign, index_assign, hungarian_min_penalty, dp_min_penalty
from players.g2.assigns import greedy_best_fit_assignment

class Strategy(Enum):
    SNEAK = "sneak"
    CLIMB_HILLS = "climb_hills"
    SAWTOOTH = "sawtooth"


class G2_Player:
    def __init__(
        self,
        rng: np.random.Generator,
        logger: logging.Logger,
        precomp_dir: str,
        tolerance: int,
    ) -> None:
        """Initialise the player with the basic information

        Args:
            rng (np.random.Generator): numpy random number generator, use this for same player behavior across run
            logger (logging.Logger): logger use this like logger.info("message")
            precomp_dir (str): Directory path to store/load pre-computation
            tolerance (int): tolerance for the cake distribution
            cake_len (int): Length of the smaller side of the cake
        """

        self.rng = rng
        self.logger = logger
        self.tolerance = tolerance
        self.cake_len = 20
        self.cake_width = 40
        self.move_queue = []

        self.strategy = Strategy.SNEAK
        self.move_object = None

    def cut(self, cut_position):
        if self.cake_width * self.cake_len < 860:
            cuts = self.sawtooth_cut(self.cake_width, self.cake_len)
            for cut in cuts:
                self.make_cut(cut) 
        else:
            cuts= self.bigcakecuts(self, self.cake_len, self.cake_width, cut_position) 

    def make_cut(self, cut_position):
        # Logic for executing a cut at cut_position
        print(f"Cutting at position: {cut_position}")
    
    def sawtooth_cut(self, cake_width, cake_len):
        slice_height = 1.6  
        cuts = []  
        current_y = 0  # Starting from the top

        while current_y < self.cake_len:
            # Cut horizontally
            cuts.append((0, current_y))  # Start from the left edge
            cuts.append((self.cake_width, current_y))  # Cut to the right edge
            current_y += slice_height  # Move down by slice height

            # If we've reached the end of the cake, break
            if current_y >= self.cake_len:
                break

            # Cut horizontally back
            cuts.append((self.cake_width, current_y))  # Start from the right edge
            cuts.append((0, current_y))  # Cut to the left edge
            current_y += slice_height  # Move down by slice height

        return cuts


    def bigcakecuts(self, cake_len, cake_width, cur_pos) -> tuple[int, List[int]]:
        if cur_pos[0] == 0:
            return constants.CUT, [cake_width, round((cur_pos[1] + 5) % cake_len, 2)]
        else:
            return constants.CUT, [0, round((cur_pos[1] + 5) % cake_len, 2)]

    def assign(
        self, assign_func: Callable[[list[Polygon], list[float]], list[int]]
    ) -> tuple[int, List[int]]:

        assignment: list[int] = assign_func(self.polygons, self.requests, self.tolerance)

        return constants.ASSIGN, assignment

    def can_cake_fit_in_plate(self, cake_piece, radius=12.5):
        cake_points = np.array(
            list(zip(*cake_piece.exterior.coords.xy)), dtype=np.double
        )
        res = miniball.miniball(cake_points)

        return res["radius"] <= radius

    def __calculate_penalty(
        self, assign_func: Callable[[list[Polygon], list[float]], list[int]]
    ) -> float:
        penalty = 0
        assignments: list[int] = assign_func(self.polygons, self.requests)

        for request_index, assignment in enumerate(assignments):
            # check if the cake piece fit on a plate of diameter 25 and calculate penaly accordingly
            if assignment == -1 or (
                not self.can_cake_fit_in_plate(self.polygons[assignment])
            ):
                penalty += 100
            else:
                penalty_percentage = (
                    100
                    * abs(self.polygons[assignment].area - self.requests[request_index])
                    / self.requests[request_index]
                )
                if penalty_percentage > self.tolerance:
                    penalty += penalty_percentage
        return penalty

    def climb_hills(self):
        current_penalty = self.__calculate_penalty(index_assign)
        print(f"1 penalty: {current_penalty}")
        current_penalty = self.__calculate_penalty(sorted_assign)
        print(f"2 penalty: {current_penalty}")

        if self.turn_number == 1:
            print()
            return constants.INIT, [0, 0]

        if len(self.polygons) < len(self.requests):
            if self.cur_pos[0] == 0:
                return constants.CUT, [
                    self.cake_width,
                    round((self.cur_pos[1] + 5) % self.cake_len, 2),
                ]
            else:
                return constants.CUT, [
                    0,
                    round((self.cur_pos[1] + 5) % self.cake_len, 2),
                ]

        return constants.ASSIGN, sorted_assign(self.polygons, self.requests)

    def process_percept(self, current_percept: PieceOfCakeState):
        self.polygons = current_percept.polygons
        self.turn_number = current_percept.turn_number
        self.cur_pos = current_percept.cur_pos
        self.requests = current_percept.requests
        self.cake_len = current_percept.cake_len
        self.cake_width = current_percept.cake_width

    def move(self, current_percept: PieceOfCakeState) -> tuple[int, List[int]]:
        """Function which retrieves the current state of the amoeba map and returns an amoeba movement"""
        self.process_percept(current_percept)

        if self.strategy == Strategy.SNEAK:
            if self.turn_number == 1:
                self.move_object = EvenCuts(
                    len(self.requests), self.cake_width, self.cake_len
                )

            move = self.move_object.move(self.turn_number, self.cur_pos)
            if move == None:
                if len(self.requests) < 10:
                    #print("Brute Force!")
                    return self.assign(greedy_best_fit_assignment)
                else:
                    return self.assign(greedy_best_fit_assignment)

            return move

        elif self.strategy == Strategy.CLIMB_HILLS:
            return self.climb_hills()

        # default
        return self.climb_hills()

    