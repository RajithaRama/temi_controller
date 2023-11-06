import robot.robot_controller as rc
from ethical_governor.ethical_governor import EthicalGovernor

TEST = 0


class RobotPlanner():
    def __init__(self, governor_conf, robot=None):
        self.robot = rc.RobotController(robot)
        self.env = None
        self.governor = EthicalGovernor(governor_conf)

    def step(self):
        self.env = self.get_perception_data()

        # print(self.env.followee_history)

        behavioural_alternatves = self.plan_next_action()

        governor_data = self.make_governor_data(behavioural_alternatves)

        print(governor_data)
        if TEST:
            ethical_recommendation = [self.stay]
        # else:
            ethical_recommendation = self.governor.recommend(governor_data)

        return self.execute(ethical_recommendation)

    def plan_next_action(self):
        buffered_instructions = self.env.robot.instruction_list

        possible_actions = []

        for instruction in buffered_instructions:

            # Planning user instructed behaviour
            if 'do_not_follow_to' in instruction.command:
                self.env.robot.not_follow_locations.append(instruction.objects[0])
                self.robot.not_follow_locations.append(instruction.objects[0])

            if 'allowed_following_to' in instruction.command:
                self.env.robot.not_follow_locations.remove(instruction.objects[0])
                self.robot.not_follow_locations.remove(instruction.objects[0])

        if self.env.followee.seen:
            possible_actions.append(self.follow)
        else:
            possible_actions.append(self.go_to_last_seen)

        # if robot in a restricted area and can see the follower move away
        if self.env.followee.seen and self.env.robot.location in self.env.robot.not_follow_locations:
            possible_actions.append(self.move_away)

        # staying the same place
        possible_actions.append(self.stay)

        # if battery level is low go to charge
        if self.env.robot.battery_level < 90:
            possible_actions.append(self.go_to_charge)

        return possible_actions

    def make_governor_data(self, behaviours):
        data = {}

        stakeholders = {}

        agent_data = {}
        if self.env.followee.seen:
            agent_data['seen'] = True
            agent_data['seen_time'] = self.env.time
            # agent_data['seen_pos'] = self.env.followee.pos
            agent_data['seen_location'] = self.env.followee.location
        else:
            agent_data['seen'] = False

        agent_data['last_seen_time'] = self.env.followee.last_seen_time
        # agent_data['last_seen_pos'] = self.env.followee.last_seen_pos
        agent_data[
            'last_seen_location'] = self.env.followee.last_known_location
        agent_data['last_moved_time'] = self.env.followee.last_moved_time

        stakeholders['followee'] = agent_data

        robot_data = {
              # 'pos': self.env.robot.pos,
              'location': self.env.robot.location,
              'not_follow_request': self.env.robot.not_follow_request,
              'not_follow_locations': self.env.robot.not_follow_locations.copy(),
              'battery_level': self.env.robot.battery_level,
              'instruction_list': self.env.robot.instruction_list.copy()
        }

        stakeholders['robot'] = robot_data

        data['stakeholders'] = stakeholders
        # env['']

        environment = {"time_of_day": self.env.time_of_day, "time": self.env.time,
                       "followee_avg_time_and_std_in_rooms": self.robot.get_followee_avg_times_and_stds(),
                       "no_of_followee_emergencies_in_past": float(self.env.followee_history),
                       "followee_health_score": float(self.env.followee_health_score),
                       "map": self.env.map,
                       }

        data['environment'] = environment
        data['suggested_actions'] = behaviours
        data['other_inputs'] = {}

        # print("robot env: " + str(data))
        return data

    def execute(self, ethical_recommendation):
        if TEST:
            ethical_recommendation = [self.stay]
            ethical_recommendation[0]()
            print('Action executed at step ' + str(self.env.time) + ': ' + str(ethical_recommendation[0]))
            return
        if len(ethical_recommendation) == 1:
            ethical_recommendation[0]()
            print('Action executed at step ' + str(self.env.time) + ': ' + str(ethical_recommendation[0]))

        else:
            # Check for low battery
            if self.env.robot.battery_level < 5 and self.charge in ethical_recommendation:
                self.charge()
                print('Action executed at step ' + str(self.env.time) + ': ' + str(self.charge))

            # Check follow
            elif self.follow in ethical_recommendation:
                self.follow()
                print('Action executed at step ' + str(self.env.time) + ': ' + str(self.follow))

            # else make the action allows the robot to stay closest to the resident
            else:
                distances = []
                for recommendation in ethical_recommendation:
                    next_location = self.robot.simulate_next_location(recommendation)
                    distances.append((recommendation, self.robot.get_shortest_distance(start=next_location,
                                                                                       target=self.env.followee.last_seen_pos)))

                distances.sort(key=lambda x: x[1])
                executing_action = distances[0][0]

                executing_action()

    def charge(self):
        self.robot.go_to_location('home base')

    def get_perception_data(self):
        if TEST == 1:
            # test 1
            perception_data = rc.PerceptionData()

            perception_data.robot.battery_level = 100
            perception_data.robot.location = 'bedroom-a'
            # perception_data.robot.pos = (8, 8)
            perception_data.robot.instruction_list = [rc.Instruction('do_not_follow_to', ['bedroom-a bed'])]
            perception_data.robot.not_follow_locations = []
            perception_data.robot.not_follow_request = []

            perception_data.followee.seen = True
            # perception_data.followee.pos = (9, 8)
            perception_data.followee.location = 'bedroom-a bed'
            perception_data.followee.last_seen_time = self.robot.get_time() - (35 * 60)
            perception_data.followee.last_known_location = 'bedroom-a bed'

            # perception_data.followee.last_seen_pos = (9, 8)

            perception_data.time = self.robot.get_time()
            perception_data.time_of_day = self.robot.get_time_of_day()
            perception_data.followee_history = int(0)
            perception_data.followee_health_score = 1
            perception_data.map = rc.map(1)

        elif TEST == 2:
            # test 2
            perception_data = rc.PerceptionData()

            perception_data.robot.battery_level = 100
            perception_data.robot.location = 'home base'
            # perception_data.robot.pos = (8, 8)
            perception_data.robot.instruction_list = [rc.Instruction('do_not_follow_to', ['bedroom-a bed'])]
            perception_data.robot.not_follow_locations = []
            perception_data.robot.not_follow_request = []

            perception_data.followee.seen = False
            # perception_data.followee.pos = (9, 8)
            perception_data.followee.location = 'bedroom-a bed'
            perception_data.followee.last_seen_time = 1699294427.3742583
            perception_data.followee.last_known_location = 'bedroom-a bed'

            # perception_data.followee.last_seen_pos = (9, 8)

            perception_data.time = self.robot.get_time()
            perception_data.time_of_day = self.robot.get_time_of_day()
            perception_data.followee_history = int(0)
            perception_data.followee_health_score = 1
            perception_data.map = rc.map(1)
            # print(perception_data.followee_history)
            return perception_data

        return self.robot.get_perception_data()

    def follow(self):
        self.robot.follow()

    def go_to_last_seen(self):
        if TEST:
            self.robot.go_to_location(self.env.followee.last_known_location)
            return
        self.robot.go_to_last_seen()

    def move_away(self, sim=False):
        # move to the closest allowed location
        map = self.robot.get_map()
        node_distance = map.get_node_distance_sorted()
        for node, distance in node_distance:
            if node in self.env.robot.not_follow_locations:
                continue
            else:
                if sim:
                    return node
                self.robot.go_to_location(node)

    def stay(self):
        if TEST:
            return
        self.robot.stay()

    def go_to_charge(self):
        self.robot.go_to_charge()


if __name__ == "__main__":
    TEST = 1
    robot = RobotPlanner(governor_conf='elder_care_sim_PSRB.yaml')
    try:
        robot.step()
    except IOError:
        print(IOError)

    # print(type(robot.env.map.location_data))
    # print(robot.env.map.location_data.nodes)
    # print(robot.env.map.location_data.edges)
    # print(robot.env.map.get_closest_locations('kitchen'))
