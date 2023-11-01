import mqtt_client


class FolloweeData:
    seen = None
    pos = None
    location = None
    last_seen_time = None
    last_seen_location = None
    last_seen_pos = None

    def __init__(self) -> None:
        pass

class RobotData:
    pos = None
    location = None
    not_follow_request = None
    not_follow_locations = None
    battery_level = None
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


class map:
    def __init__(self, map_id, location_data, map_area, home_coordinates) -> None:
        self.map_id = map_id
        self.location_data = location_data
        self.map_area = map_area # coordinates and connections of locations as array.
        self.home_coordinates = home_coordinates # coordinates of the home location
        self.robot_location = self.home_coordinates
        self.followee_location = None

    def set_robot_location(self, location):
        self.robot_location = location

    def set_followee_location(self, location):
        self.followee_location = location


class Instruction:
    command = None
    objects = None

    def __init__(self, command, objects) -> None:
        self.command = command
        self.objects = objects


class RobotController():
    def __init__(self, robot=mqtt_client.CLIENT_ADDRESS):
        self.robot = mqtt_client.MQTTConnect(client_address=robot)
        
        # Connect to the robot
        self.robot.connect()

        self.not_follow_locations = []

        self.followee_last_seen_time = None
        self.followee_last_seen_location = None
        self.followee_last_seen_pos = None

        self.followee_history = 0
        self.followee_health_score = 1

        self.follower_avg_time_and_std_in_rooms = {'bathroom': (20, 10), 'kitchen': (60, 10),
                                            'hall': (10, 5), 'bedroom': (20, 10), 'bedroom_close_bed': (60, 15)}

        self.time_of_day = 'day'


    def get_perception_data(self):
        perception_data = PerceptionData()

        perception_data.robot.battery_level = self.get_battery_level()
        perception_data.robot.location = self.get_location()
        perception_data.robot.pos = self.get_pos()
        perception_data.robot.instruction_list = self.get_instruction_list()
        perception_data.robot.not_follow_locations = self.get_not_follow_locations()
        perception_data.robot.not_follow_request = self.get_not_follow_request()

        perception_data.followee.seen = self.get_followee_seen()
        perception_data.followee.pos = self.get_followee_pos() if perception_data.followee.seen else None
        perception_data.followee.location = self.get_followee_location() if perception_data.followee.seen else None
        perception_data.followee.last_seen_time = self.get_followee_last_seen_time()
        perception_data.followee.last_seen_location = self.get_followee_last_seen_location()
        perception_data.followee.last_seen_pos = self.get_followee_last_seen_pos()

        perception_data.time = self.get_time()
        perception_data.time_of_day = self.get_time_of_day()
        perception_data.followee_history: self.get_followee_history()
        perception_data.followee_health_score: self.get_followee_health_score()
        perception_data.map: self.get_map()

        return perception_data
        
    ############# actions ###############
    def follow(self):
        # Follow the user

        pass

    def go_to_last_seen(self):
        # Go to the last seen location
        pass

    def move_away(self):
        # Move to the closest allowed location.
        pass

    def stay(self):
        # Stay in the same place
        pass

    def go_to_charge(self):
        # Go to the charging station
        pass

    # Note: Replace spaces in the variables with '_'
    ############# getters ###############
    def get_battery_level(self):
        # Get the battery level
        pass

    def get_location(self):
        # Get the current location
        return self.robot.get_robot_location()

    def get_pos(self):
        # Get the current position
        pass

    def get_instruction_list(self):
        # Get the list of instructions
        pass

    def get_followee_seen(self):
        # Get whether the followee is seen
        pass

    def get_followee_pos(self):
        # Get the followee position
        pass

    def get_followee_location(self):
        # Get the followee location
        pass

    def get_followee_last_seen_time(self):
        # Get the followee last seen time
        if self.get_followee_seen():
            self.followee_last_seen_time = self.get_time()
        return self.followee_last_seen_time
        
    def get_followee_last_seen_location(self):
        # Get the followee last seen location
        if self.get_followee_seen():
            self.followee_last_seen_location = self.get_followee_location()
        return self.followee_last_seen_location
    
    def get_followee_last_seen_pos(self):
        # Get the followee last seen position
        if self.get_followee_seen():
            self.followee_last_seen_pos = self.get_followee_pos()
        return self.followee_last_seen_pos
    
    def get_time(self):
        # Get the current time
        pass
    
    def get_followee_history(self):
        # Get the followee history
        return self.followee_history
        
    def get_followee_health_score(self):
        # Get the followee health score
        return self.followee_health_score
        
    def get_map(self):
        # Get the map
        pass

    def get_follower_avg_times_and_stds(self):
        # Get the average times and stds
        return self.follower_avg_time_and_std_in_rooms
    
    def get_not_follow_locations(self):
        # Get the not follow locations
        pass

    def get_not_follow_request(self):
        # Get the not follow request
        pass

    def get_time_of_day(self):
        # Get the time of day
        return self.time_of_day

    def get_shortest_distance(self, start, target):
        # Get the shortest distance between two points
        pass