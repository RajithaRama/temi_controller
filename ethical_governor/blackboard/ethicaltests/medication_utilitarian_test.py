import numpy as np
from scipy.stats import gamma

import ethical_governor.blackboard.ethicaltests.ethical_test as ethical_test
import agent_types.medication_robot as ROBOT

RESOLUTION = 0.1


class MedicationUtilitarianTest(ethical_test.EthicalTest):

    def __init__(self, test_data):
        super().__init__(test_data)
        self.instruction_function_map = {
            'SNOOZE': [True, ROBOT.Robot.snooze.__name__],
            'ACKNOWLEDGE': [True, ROBOT.Robot.acknowledge.__name__]
        }

    def run_test(self, data, logger):
        logger.info('Running ' + __name__ + '...')
        env = data.get_environment_data()
        stakeholder_data = data.get_stakeholders_data()

        for action in data.get_actions():
            utils = {}

            logger.info('Testing action: ' + str(action.value))

            # logger.info('Calculating autonomy utility for stakeholders')
            autonomy_utility = self.get_autonomy_utility(env=env, stakeholder_data=stakeholder_data, action=action,
                                                         logger=logger)
            # logger.info('Autonomy utilities for action ' + str(action.value) + ': ' + str(autonomy_utility))
            utils['autonomy'] = autonomy_utility

            # logger.info('Calculating well-being utility for stakeholders')
            wellbeing_util = self.get_wellbeing_utility(env=env, stakeholder_data=stakeholder_data, action=action,
                                                        logger=logger)
            # logger.info('Wellbeing utilities for action ' + str(action.value) + ': ' + str(wellbeing_util))
            utils['wellbeing'] = wellbeing_util

            out = {}
            for util_type, values in utils.items():
                if util_type == 'wellbeing':
                    for stakeholder, util_value, probability, prob_dist in values:
                        col_name_util = stakeholder + '_' + util_type
                        col_name_prob = stakeholder + '_' + 'wellbeing_probability'
                        col_name_dist = stakeholder + '_' + 'wellbeing_distribution'
                        out[col_name_util] = util_value
                        out[col_name_prob] = probability
                        out[col_name_dist] = prob_dist
                else:
                    for stakeholder, util_value in values:
                        col_name = stakeholder + '_' + util_type
                        out[col_name] = util_value
            self.output[action] = out

    def get_autonomy_utility(self, env, stakeholder_data, action, logger):
        """
        Calculating autonomy  values for stakeholders.
        When the robot does not follow a user command, autonomy value for that user is -1, if it follows 1 and the
        default is 0.
        - return: list with (stakeholder_id, autonomy utility) tuples
        """

        instruction_list = stakeholder_data['robot']['instruction_list']

        stakholder_autonomy_values = []

        for stakeholder, data in stakeholder_data.items():
            # skip for robot
            if stakeholder == 'robot':
                continue

            autonomy_utility = 0.0

            if data['attached_reminders']:
                try:
                    for instruction in instruction_list:
                        if instruction[1].id == stakeholder_data[stakeholder]['id']:
                            if self.instruction_function_map[instruction[0]][1] == action.value[0].__name__:
                                autonomy_utility = 1.0
                            else:
                                autonomy_utility = -0.7
                except TypeError:
                    pass
                
                if autonomy_utility == 0.0:
                    if action.value[0].__name__ == 'followup':
                        autonomy_utility = -0.1 * data['attached_reminders']['no_of_followups']
                        autonomy_utility = max(autonomy_utility, -1)
                    elif action.value[0].__name__ == 'record':
                        autonomy_utility = 0.5
                    elif action.value[0].__name__ == 'record_and_call_careworker':
                        autonomy_utility = -0.7

            stakholder_autonomy_values.append((stakeholder, autonomy_utility))

        return stakholder_autonomy_values

    def get_wellbeing_utility(self, env, stakeholder_data, action, logger):
        """
        Calculates the wellbeing utility distribution for each stakeholder, given the current state of the environment, and the next action.
        returns a list of tuples (stakeholder_id, Highest probable wellbeing utility, probability, probability_dist) 
        variables:
        - e_m = effect of the medication
        - d_m = Number of continuously missing doses

        b=1-e^{\left(-\left(d+f-1.5\right)\right)}
        g=\left(\frac{f}{2}\right)\ln\left(2d+1\right)

        y\ =\frac{g}{\sqrt{2\pi}}\exp\left(-g\left(x+b\right)^{2}\right)

        """

        # visible_stakeholders = stakeholder_data['robot']['model'].model.visible_stakeholders(
        #     center_agent_pos=next_pos, visibility_radius=ROBOT.VISIBLE_DIST)
        # visible_stakeholders_ids = [stakeholder.id for stakeholder in visible_stakeholders]

        stakholder_wellbeing_values = []

        for stakeholder, data in stakeholder_data.items():
            if stakeholder == 'robot':
                continue

            wellbeing_util = 0.0
            proba = 1.0
            prob_dist = np.ones(int(2 / RESOLUTION + 1))

            if data['attached_reminders']:

                e_m = env['Medication_info'][data['attached_reminders']['med_name']]['impact'].value
                d_m = data['attached_reminders']['timer'].no_of_missed_doses

                if data['attached_reminders']['state'] == ROBOT.ReminderState.ISSUED:
                    if action.value[0].__name__ == 'snooze':
                        d_m += (data['attached_reminders']['no_of_followups'] + 1) / 8
                        wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)  
                    elif action.value[0].__name__ == 'record':
                            d_m += 1
                            wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)
                    elif action.value[0].__name__ == 'record_and_call_careworker':
                        d_m += 1
                        wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)
                        wellbeing_util = abs(wellbeing_util)  

                elif data['attached_reminders']['state'] == ROBOT.ReminderState.SNOOZED:
                    if not action.value[0].__name__ == 'remind_medication':
                        d_m += data['attached_reminders']['no_of_snoozes'] / 3
                        wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)
                    else:
                        d_m += 1
                        wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)
                        wellbeing_util = abs(wellbeing_util)

                elif data['attached_reminders']['state'] == ROBOT.ReminderState.ACKNOWLEDGED:
                    if not data['took_meds']:
                        if action.value[0].__name__ == 'followup':
                            d_m += data['attached_reminders']['no_of_followups'] / 4
                            # wellbeing lost (or gained) by delaying the medication + wellbeing gained by nudging towards taking the medication
                            wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)
                            # if wellbeing is negative, Wellbeing gained by nudging = 0.5 (fixed)
                            wellbeing_util += 0.5
                        
                        elif action.value[0].__name__ == 'record':
                            d_m += 1
                            wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)
                        elif action.value[0].__name__ == 'record_and_call_careworker':
                            d_m += 1
                            wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)
                            wellbeing_util = abs(wellbeing_util)

            else:
                if action.value[0].__name__ == 'remind_medication' and action.value[1].recipient == stakeholder:
                    e_m = env['Medication_info'][action.value[1].med_name]['impact'].value
                    d_m = action.value[1].no_of_missed_doses + 1
                    wellbeing_util, proba, prob_dist = self.calculate_wellbeing_values(e_m, d_m)
                    wellbeing_util = abs(wellbeing_util)

            stakholder_wellbeing_values.append((stakeholder, wellbeing_util, proba, prob_dist))

        return stakholder_wellbeing_values

    def calculate_wellbeing_values(self, e_m, d_m, resolution=RESOLUTION):
        """
        Calculate the wellbeing values for the stakeholder
        """

        highest_prob_util, proba = self.highest_probable_utility(e_m, d_m, resolution/2)
        _, prob_dist = self.Utility_dist(e_m, d_m, resolution)

        return highest_prob_util, proba, prob_dist

    def highest_probable_utility(self, e_m, d_m, resolution=0.1):
        "Calculate the highest probable utility of the stakeholder"

        if d_m > 0:
            x, y = self.Utility_dist(e_m, d_m, resolution)
            max_prob = max(y)
            utility = x[y.index(max_prob)]

            
            utility = utility if (max_prob > 0.05) and (utility < 0.0) else 0.0

        else:
            utility = 0.0
            max_prob = 1.0

        return round(utility, 5), round(max_prob, 5)

    # ///////// OLD CODE
    # def get_low_res_probability_dist(self, e_m, d_m, resolution=0.1):
    #     """Generate a low resolution probability distribution of the utility of stakeholder
    #     """
    #     low_res_probs = np.zeros(int((2 / resolution) + 1))
    #     if d_m > 0:
    #         x, y = self.Utility_dist(e_m, d_m, resolution)
    #         i = 0
    #         x = x.round(5).tolist()
    #         # space = np.linspace(-1, 1, int(2/resolution + 1))
    #         indexes = [x.index(e) for e in np.linspace(-1, 1, int(2 / resolution + 1)).round(5)]
    #         for j in indexes:
    #             low_res_probs[i] = y[j].round(5)
    #             i += 1

    #     return low_res_probs

    # 
    # def Utility_dist(self, e_m, d_m):
    #     """Generate a probability distribution of the utility of stakeholder
    #     """

    #     d = d_m
    #     f = e_m
    #     b = 1 - np.exp(-1 * (d + f - 1.5))
    #     g = (f / 2) * np.log(2 * d + 1)

    #     x, step = np.linspace(-1, 1, 101, retstep=True)
    #     # print(step)

    #     y = (g / np.sqrt(2 * np.pi)) * np.exp(-g * (x + b) ** 2)

    #     return x, y

    def Utility_dist(self, e_m, d_m, resolution=0.1):
        """Generate a probability distribution of the utility of stakeholder
        """

        d = d_m
        f = e_m
        
        a = 1.325*f*f - 9.475*f + 18.15
        scale = np.exp(-2.65 - (d/2)) + 0.01 # q
        loc = -1

        domain = np.linspace(-1, 1, int(2 / resolution + 1)).round(5).tolist()

        x = []
        y = []
        for i in range((len(domain) - 1)):
            # print(i)
            x.append((domain[i+1] + domain[i])/2)
            y.append(gamma.cdf(domain[i+1], a=a, loc=loc, scale=scale) - gamma.cdf(domain[i], a=a, loc=loc, scale=scale))

        return x, y