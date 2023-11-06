import robot.robot_planner as rp
import time

rp.TEST = 2

if __name__ == "__main__":
    robot = rp.RobotPlanner(governor_conf='elder_care_sim_PSRB.yaml')
    while True:
        try:
            robot.step()
            time.sleep(5)
        except IOError:
            print(IOError)

