from openhab import OpenHAB

URL = "http://192.168.2.34:8080/rest"
USERNAME = "openhab-user"
PASSWORD = "password"

locations_items_map = {
    'bathroom': "BATHROOM__Motion_sensor__Motion_Intrusion",
    'bedroom-a': "BEDROOM_A__Motion_sensor__Motion_Intrusion",
    'bedroom-b': "BEDROOM_B__Motion_sensor__Motion_Intrusion",
    'bedroom-a bed': "BEDROOM_A__Motion_sensor__Motion_Intrusion",
    'bedroom-b bed': "BEDROOM_B__Motion_sensor__Motion_Intrusion",
    'living room': "LIVING_ROOM__Motion_sensor__Motion_Intrusion",
    'dining table': "DINNING_ROOM__Motion_sensor__Motion_Intrusion",
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

    def get_robot_location(self):
        # TODO: Implement after the android app have the feature
        self.robot_location = "home base"
        return self.robot_location
    def get_resident_location(self):
        # check the presence sensor identify anything. If there is more than one, eliminate the location where robot located.
        presence_detected_locations = []
        for location in self.locations:
            sensor = self.oh.get_item(locations_items_map[location])

            if sensor.state == "ON":
                presence_detected_locations.append(location)

        if len(presence_detected_locations) == 0:
            raise IOError("Sensors does not pick anyone in the home.")

        elif len(presence_detected_locations) == 1:
            return presence_detected_locations[0]

        else:
            presence_detected_locations.remove(self.robot_location)
            return presence_detected_locations[0]


    ############# Actions #############
    def go_to_location(self, location):
        robot = self.oh.get_item('TemiRobot_GoTo_Location')
        return robot.command(location)

    def follow(self):
        robot = self.oh.get_item("TemiRobot_Follow_Me")
        return robot.command("ON")


if __name__== "__main__":

    connection = OpenHABConnect(locations=['bathroom', 'bedroom-a', 'bedroom-b', 'bedroom-a bed', 'bedroom-b bed', 'living room', 'dining table', 'kitchen'])
    connection.connect()

    # print(connection.get_resident_location())
    # print(connection.follow())
    # data = connection.oh.fetch_all_items()
    # kitchen_sense = connection.oh.get_item('KITCHEN__Motion_sensor_1_Motion_Intrusion')
    # print(kitchen_sense)

    # print(connection.go_to_location('kitchen'))
    print(connection.go_to_location('home base'))

    # print(data)