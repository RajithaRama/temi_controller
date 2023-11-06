import threading
import time
import paho.mqtt.client as mqtt

CLIENT_ADDRESS = "192.168.2.167"
CLIENT_PORT = 1883
USERNAME = "mqtt-user"
PASSWORD = "password"

class MQTTConnect:
    def __init__(self, client_address=CLIENT_ADDRESS, client_port=CLIENT_PORT, username=USERNAME, password=PASSWORD):
        self.client_address = client_address
        self.client_port = client_port
        self.username = username
        self.password = password

        self.robot_location = None
        

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))    

    def on_message(self, client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))

    def on_publish(self, client, userdata, mid):
        print("published with mid: "+str(mid)) 

    def on_subscribe(self, client, userdata, mid, granted_qos):
        print("Subscribed: "+str(mid)+" "+str(granted_qos))

    def on_disconnect(self, client, userdata, rc):
        print("Disconnected with result code "+str(rc))

    def connect(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(self.username, self.password)
        # client.tls_set(ca_certs=ssl.CERT_REQUIRED)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        self.client.connect(self.client_address, self.client_port, 60)
        self.client.loop_start()

        # subcribing to topics
        self.get_location_sub()


    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    ############# Actions #############
    def go_to_location(self, location):
        rc = self.client.publish("RoboConnect/TemiRobot/launchHandler/serviceGoTo/set", location)
        rc.wait_for_publish()


    ############# Perception #############

    #### subscriptions ####
    def get_robot_location_sub(self):
        self.client.subscribe("RoboConnect/TemiRobot/launchHandler/serviceGoTo")
        self.sem_get_location = threading.Semaphore()
        self.client.message_callback_add("RoboConnect/TemiRobot/launchHandler/serviceGoTo", self.on_get_robot_location_message)


    #### on message callbacks ####
    def on_get_robot_location_message(self, client, userdata, msg):
        with self.sem_get_location:
            self.robot_location = msg.payload.decode('utf-8')
        print("robot_location: " + self.robot_location)


    #### getters ####
    def get_robot_location(self):
        with self.sem_get_location:
            return self.robot_location


if __name__ == '__main__':
    mqtt_connect = MQTTConnect()
    mqtt_connect.connect()
    mqtt_connect.get_location()
    time.sleep(10)
    mqtt_connect.go_to_location("sofa")
    time.sleep(10)
    mqtt_connect.go_to_location("home base")
    mqtt_connect.disconnect()