import robot.mqtt_client as mqtt_client
import robot.openhab_client as openhab_client
import time
import networkx as nx


class FolloweeData:
    seen = None
    # pos = None
    location = None
    last_seen_time = None
    last_known_location = None
    last_moved_time = None

    # last_seen_pos = None

    def __init__(self) -> None:
        pass


class RobotData:
    # pos = None
    location = None
    not_follow_request = None
    not_follow_locations = None
    # battery_level = None
    instruction_list = None

    def __init__(self) -> None:
        pass


class PerceptionData:
    followee = FolloweeData()
    robot = RobotData()
    time = None
    time_of_day = None
    followee_history = None
    followee_health_score = None
    map = None


lab_location_data = {
    'home base': {'kitchen': {'weight': 1}, 'bathroom': {'weight': 2}, 'bedroom-a bed': {'weight': 2},
                  'bedroom-a': {'weight': 3}},
    'kitchen': {'dinning table': {'weight': 1}, 'living room': {'weight': 1}},
    'dinning table': {'living room': {'weight': 1}},
    'living room': {'bedroom-b': {'weight': 1}, 'bedroom-b bed': {'weight': 1}},
    'bedroom-b': {'bedroom-b bed': {'weight': 1}, 'bedroom-a': {'weight': 1}},
    'bedroom-b bed': {'bedroom-a': {'weight': 1}},
    'bedroom-a': {'bedroom-a bed': {'weight': 1}, 'bathroom': {'weight': 1}},
}
lab_location_boundries = {
    'home base': [((0.00, 0.3), (-0.4, 0.3))],
    'kitchen': [((0.263,2), (-3.6, -0.9)), ((2.2, 8), (0, 1))],
    'bathroom': [((3.9, 6.2), (-3, -0.2))],
    'bedroom-a': [((6.2, 7.6), (-3.1, -0.15))],
    'bedroom-a bed': [((7.6, 8), (-1.6, -0.2))]
}

class map:
    def __init__(self, map_id, location_data=lab_location_data, map_area=None, home_coordinates=None) -> None:
        self.map_id = map_id
        self.location_data = nx.Graph(location_data)  # location data as a graph
        self.map_area = map_area  # coordinates and connections of locations as array.
        self.home_coordinates = home_coordinates  # coordinates of the home location
        self.robot_location = self.home_coordinates
        self.followee_location = None

    def set_robot_location(self, location):
        self.robot_location = location

    def set_followee_location(self, location):
        self.followee_location = location

    def get_closest_locations(self, location):
        distances = self.get_node_distance_sorted(location)
        return distances[0][0]

    def get_node_distance_sorted(self, start):
        # return [(node, distance)]
        distances = []
        for node in self.location_data.nodes:
            distances.append((node, nx.shortest_path_length(self.location_data, start, node, weight='weight')))
        # print(distances)
        distances.sort(key=lambda x: x[1])
        return distances

    def get_shortest_path_distance(self, start, end):
        return nx.shortest_path_length(self.location_data, start, end, weight='weight')


class Instruction:
    command = None
    objects = None

    def __init__(self, command, objects) -> None:
        self.command = command
        self.objects = objects


class RobotController:
    def __init__(self, robot=mqtt_client.CLIENT_ADDRESS):
        # self.robot = mqtt_client.MQTTConnect(client_address=robot)
        self.robot = openhab_client.OpenHABConnect(
            locations=['bathroom', 'bedroom-a', 'bedroom-b', 'bedroom-a bed', 'bedroom-b bed', 'living room',
                       'dinning table', 'kitchen'])
        # Connect to the robot
        self.robot.connect()

        self.not_follow_locations = []

        self.robot_last_known_location = None
        self.robot_last_behaviour = None

        self.followee_last_seen_time = None
        self.followee_last_known_location = None
        self.followee_last_known_time = None
        self.followee_last_seen_pos = None

        self.followee_history = 0
        self.followee_health_score = 1

        self.follower_avg_time_and_std_in_rooms = {'bathroom': (20, 10), 'kitchen': (60, 10),
                                                   'living room': (60, 10), 'bedroom-a': (20, 10),
                                                   'bedroom-a bed': (60, 15), 'bedroom-b': (20, 10),
                                                   'bedroom-b bed': (60, 15), 'dinning table': (30, 10)}
        self.time_of_day = 'day'

        self.battery = 100
        self.step = 0

    def get_perception_data(self):
        perception_data = PerceptionData()

        perception_data.robot.battery_level = self.get_battery_level()
        perception_data.robot.location = self.get_location()
        perception_data.robot.pos = self.get_pos()
        perception_data.robot.instruction_list = self.get_instruction_list()
        perception_data.robot.not_follow_locations = self.get_not_follow_locations()
        # perception_data.robot.not_follow_request = self.get_not_follow_request()

        perception_data.followee.seen = self.get_followee_seen()
        # perception_data.followee.pos = self.get_followee_pos() if perception_data.followee.seen else None
        perception_data.followee.location = self.get_followee_location()
        perception_data.followee.last_seen_time = self.get_followee_last_seen_time()
        perception_data.followee.last_known_location = self.get_followee_last_known_location()
        perception_data.followee.last_moved_time = self.followee_last_known_time
        # perception_data.followee.last_seen_pos = self.get_followee_last_seen_pos()

        perception_data.time = self.get_time()
        perception_data.time_of_day = self.get_time_of_day()
        perception_data.followee_history = self.get_followee_history()
        perception_data.followee_health_score = self.get_followee_health_score()
        perception_data.map = self.get_map(1)

        return perception_data

    ############# actions ###############
    def follow(self):
        # Follow the user
        self.robot.follow(True)
        self.robot_last_known_location = self.followee_last_known_location
        self.robot_last_behaviour = self.follow
        pass

    def go_to_last_seen(self):
        # Go to the last seen location
        self.stop_last_behaviour()
        ret = self.robot.go_to_location(self.followee_last_known_location)
        if ret == 1:
            self.robot_last_known_location = self.followee_last_known_location
            self.robot_last_behaviour = self.go_to_last_seen
            return 1
        else:
            self.robot.go_to_location(self.robot_last_known_location)
            return -1

    def go_to_location(self, location):
        # Move to the closest allowed location.
        ret = self.robot.go_to_location(location)
        self.stop_last_behaviour()
        if ret == 1:
            self.robot_last_known_location = location
        else:
            self.robot.go_to_location(self.robot_last_known_location)
        self.robot_last_behaviour = self.go_to_location

    def stay(self):
        # Stay in the same place
        if self.robot_last_behaviour == self.follow:
            self.robot.follow(on=False)
            return 1
        elif self.robot_last_behaviour == self.go_to_location:
            current_location = self.get_location()
            if current_location is not None:
                return 1
            else:
                return self.go_to_location(self.robot_last_known_location)

    def go_to_charge(self):
        # Go to the charging station
        self.stop_last_behaviour()
        self.robot.go_to_location("home base")
        self.robot_last_known_location = "home base"
        self.robot_last_behaviour = self.go_to_charge
        pass

    def stop_last_behaviour(self):
        if self.robot_last_behaviour == self.follow:
            self.robot.follow(False)

    # Note: Replace spaces in the variables with '_'
    ############# getters ###############
    def get_battery_level(self):
        # Get the battery level

        # return self.robot.get_battery_level()
        # custom battery value for simulations
        if self.get_location() == 'home base':
            if self.battery < 98:
                self.battery += 2
        else:
            self.battery -= 0.2

        return self.battery


    def get_location(self):
        # Get the current location
        # Workaround: if the robot is in the followee location or last known location, assuming the robot sees the resident

        # if self.robot_last_behaviour == self.follow and self.robot.get_resident_seen():
        #     location = self.get_followee_location()
        #     return location if location is not None else self.followee_last_known_location
        # else:
        #     location = self.robot.get_robot_location()
        #     # returning the last known location
        #     if location is not None:
        #         self.robot_last_known_location = location
        #         return location
        #     else:
        #         return self.robot_last_known_location

        pos = self.get_pos()
        if pos is not None:
            for location, boundries in lab_location_boundries.items():
                for boundry in boundries:
                    if boundry[0][0] < pos[0] < boundry[0][1] and boundry[1][0] < pos[1] < boundry[1][1]:
                        return location
            # if not found in boundries
            location = self.robot.get_robot_location()
                # returning the last known location
            if location is not None:
                self.robot_last_known_location = location
                return location
            else:
                return self.robot_last_known_location

    def get_pos(self):
        # Get the current position
        return self.robot.get_robot_position()

    def get_instruction_list(self):
        # Get the list of instructions
        # Hardcoded instructions for now
        instructions = [Instruction(command='do_not_follow_to', objects=['bathroom']),
                        Instruction(command='do_not_follow_to', objects=['bedroom-a bed']),
                        Instruction(command='do_not_follow_to', objects=['bedroom-b bed'])]
        return instructions

    def get_followee_seen(self):
        # Get whether the followee is seen
        # Workaround: if the robot is in the followee location or last known location, assuming the robot sees the resident
        # robot_loc = self.get_location()
        # if robot_loc is not None:
        #     if robot_loc == self.get_followee_location():
        #         return True
        #     if robot_loc == self.get_followee_last_known_location():
        #         return True
        seen = self.robot.get_resident_seen()
        if seen:
            self.followee_last_seen_time = self.get_time()
            self.followee_last_known_time = self.get_time()
            return seen
        else:
            if self.get_followee_location() == "bedroom-a bed":
                self.followee_last_seen_time = self.get_time()
                self.followee_last_known_time = self.get_time()
                return True
            elif self.followee_last_known_location is not None and self.followee_last_known_location == self.get_location():
                return True
            else:
                return False
        # return self.robot.get_resident_seen()

    def get_followee_pos(self):
        # Get the followee position
        pass

    def get_followee_location(self):
        # Get the followee location
        try:
            location = self.robot.get_resident_location()
            self.followee_last_known_location = location
            self.followee_last_known_time = self.get_time()
        except IOError:
            location = None
        return location

    def get_followee_last_seen_time(self):
        # Get the followee last seen time
        if self.get_followee_seen():
            self.followee_last_seen_time = self.get_time()
            self.followee_last_known_time = self.get_time()
        return self.followee_last_seen_time

    def get_followee_last_known_location(self):
        # Get the followee last seen location
        try:
            location = self.robot.get_resident_location()
            self.followee_last_known_location = location
            self.followee_last_known_time = self.get_time()
        except IOError:
            location = self.followee_last_known_location
        return location

    def get_followee_last_seen_pos(self):
        # Get the followee last seen position
        if self.get_followee_seen():
            self.followee_last_seen_pos = self.get_followee_pos()
        return self.followee_last_seen_pos

    def get_time(self):
        # Get the current time
        return time.time()
        pass

    def get_followee_history(self):
        # Get the followee history
        return self.followee_history

    def get_followee_health_score(self):
        # Get the followee health score
        return self.followee_health_score

    def get_map(self, id):
        # Get the map
        self.map = map(id)
        self.map.set_robot_location(self.get_location())
        self.map.set_followee_location(self.get_followee_location())
        return self.map

    def get_followee_avg_times_and_stds(self):
        # Get the average times and stds
        return self.follower_avg_time_and_std_in_rooms

    def get_not_follow_locations(self):
        # Get the not follow locations
        self.not_follow_locations = []
        for instruction in self.get_instruction_list():
            if instruction.command == "do_not_follow_to":
                self.not_follow_locations.append(instruction.objects[0])

        return self.not_follow_locations

    def get_not_follow_request(self):
        # Get the not follow request
        pass

    def get_time_of_day(self):
        # Get the time of day
        return self.time_of_day

    def get_shortest_distance(self, start, target):
        # Get the shortest distance between two points
        return self.map.get_shortest_path_distance(start=start, end=target)
        pass



if __name__ == "__main__":
    controller = RobotController()
    map = controller.get_map(1)
    # print(map.location_data)

    print(controller.get_location())
    controller.robot.follow(on=True)
    time.sleep(10)
    controller.robot.follow(on=False)
    print(controller.get_location())
    close_loc = map.get_node_distance_sorted('kitchen')
