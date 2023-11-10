import time
import re

from openhab import OpenHAB

URL = "http://192.168.2.34:8080/rest"
USERNAME = "openhab-user"
PASSWORD = "password"

locations_items_map = {
    'bathroom': "BATHROOM__Motion_sensor__Motion_Intrusion",
    'bedroom-a': "BEDROOM_A__Motion_sensor__Motion_Intrusion",
    'bedroom-b': "BEDROOM_B__Motion_sensor__Motion_Intrusion",
    'bedroom-a bed': "test_switch_Contact_Portal_1",
    # 'bedroom-b bed': "BEDROOM_B__Motion_sensor__Motion_Intrusion",
    'living room': "LIVING_ROOM__Motion_sensor__Motion_Intrusion",
    'dinning table': "DINNING_ROOM__Motion_sensor__Motion_Intrusion",
    'kitchen': "KITCHEN__Motion_sensor_1_Motion_Intrusion"
}


class OpenHABConnect:
    def __init__(self, server_URL=URL, username=USERNAME, password=PASSWORD, locations=None):
        self.server_url = server_URL
        self.username = username
        self.password = password

        self.robot_location = None

        self.locations = locations

    def connect(self):
        try:
            self.oh = OpenHAB(self.server_url)
        except Exception:
            raise IOError("404 error")

    ####### Getters ###############

    def get_battery_level(self):
        battery = self.oh.get_item('TemiRobot_Battery_Status')
        str_state = str(battery.state)
        # remove spaces, split from ':' and remove percentage
        str_state = str_state.replace(" ", "")
        str_state = str_state.split(':')[1] if ':' in str_state else str_state
        str_state = str_state.replace("%", "")
        return int(str_state)

    def get_robot_location(self):
        robot_goto_state = self.oh.get_item('TemiRobot_GoTo_Location_extension')
        location, state = str(robot_goto_state.state).split(';')[:2]
        if state == "complete":
            self.robot_location = location
        else:
            self.robot_location = None
        return self.robot_location

    def get_robot_position(self):
        robot_position = self.oh.get_item('TemiRobot_Current_Position')

        # define the string
        s = str(robot_position.state)

        # use re.search to find the values of x and y
        match = re.search(r"x=(\S+), y=(\S+),", s)

        # if a match is found, extract the values and convert them to float
        if match:
            x = float(match.group(1))
            y = float(match.group(2))
            return (x, y)
        else:
            return None
    def get_resident_location(self):
        # check the presence sensor identify anything. If there is more than one, eliminate the location where robot located.

        # add bed location code
        # bed-a_bed = self.oh.get_item()
        presence_detected_locations = []
        for location in self.locations:
            try:
                sensor = self.oh.get_item(locations_items_map[location])
            except KeyError:
                continue
            if location == "bedroom-a bed":
                if sensor.state == "OPEN":
                    presence_detected_locations.append(location)
                    continue
            if sensor.state == "ON":
                presence_detected_locations.append(location)



        if len(presence_detected_locations) == 0:
            raise IOError("Sensors does not pick anyone in the home.")

        elif len(presence_detected_locations) == 1:
            return presence_detected_locations[0]

        else:
            try:
                presence_detected_locations.remove(self.robot_location)
            except ValueError:
                pass
            if "bedroom-a bed" in presence_detected_locations and "bedroom-a" in presence_detected_locations:
                presence_detected_locations.remove("bedroom-a")
            return presence_detected_locations[0]

    def get_resident_seen(self):
        robot_follow_state = self.oh.get_item("TemiRobot_Follow_Me")
        if robot_follow_state.state in ["abort", "OFF"]:
            return False
        for i in range(4):
            state_str = str(robot_follow_state.state)
            if state_str == "track":
                return True
            else:
                time.sleep(1)
                robot_follow_state = self.oh.get_item("TemiRobot_Follow_Me")
                continue
        return False

    ############# Actions #############
    def go_to_location(self, location):
        robot = self.oh.get_item('TemiRobot_GoTo_Location')

        robot.command(location)
        time.sleep(1)
        robot_feedback = self.oh.get_item('TemiRobot_GoTo_Location_extension')
        state = str(robot_feedback.state).split(';')[1]
        timer = 0
        while state not in ['complete', 'abort']:
            time.sleep(1)
            if timer > 90:
                break
            timer += 1
            state = str(robot_feedback.state).split(';')[1]
        if timer > 90:
            return -1
        else:
            return 1

    def follow(self, on):
        robot = self.oh.get_item("TemiRobot_Follow_Me")
        if on:
            return robot.command("ON")
        else:
            return robot.command("OFF")


if __name__ == "__main__":
    connection = OpenHABConnect(
        locations=['bathroom', 'bedroom-a', 'bedroom-b', 'bedroom-a bed', 'bedroom-b bed', 'living room',
                   # 'dinning table',
                   'kitchen'])
    connection.connect()

    # print(connection.get_resident_location())
    # print(connection.follow(on=True))
    # data = connection.oh.fetch_all_items()
    # kitchen_sense = connection.oh.get_item('KITCHEN__Motion_sensor_1_Motion_Intrusion')
    # print(kitchen_sense)
    # print(connection.get_robot_position())
    # time.sleep(10)
    # print(connection.follow(on=False))
    print(connection.get_resident_location())
    # print(connection.go_to_location('dining room'))
    # print(connection.get_robot_position())

    # print(connection.get_robot_location())
    # print(connection.go_to_location('home base'))
    #
    #
    # print(connection.get_battery_level())
    # print(connection.get_robot_location())
    # print(data)
