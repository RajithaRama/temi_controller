import numpy as np

import ethical_governor.blackboard.ethicaltests.ethical_test as ethical_test
import agent_types.tele_presence_robot as ROBOT
from agent_types.caller import CALLER_TYPE


class TelePresenceUtilitarianTest(ethical_test.EthicalTest):

    def __init__(self, test_data):
        super().__init__(test_data)
        self.instruction_function_map = {
            'go_forward':ROBOT.Robot.move_forward.__name__,
            'go_right': ROBOT.Robot.move_right.__name__,
            'go_backward': ROBOT.Robot.move_backward.__name__,
            'go_left': ROBOT.Robot.move_left.__name__,
            'call': ROBOT.Robot.take_call.__name__
        }

        # in this environment, the only action that constrain user is not moving away
        self.actions_related_constrained_user = ['move_away']

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

            # logger.info('Calculating the privacy for stakeholders')
            privacy_util = self.get_privacy_utility(env=env, stakeholder_data=stakeholder_data, action=action,
                                                           logger=logger)
            # logger.info('privact utils for action ' + str(action.value) + ': ' + str(privacy_util))
            utils['privacy'] = privacy_util

            out = {}
            for util_type, values in utils.items():
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

        instruction_givers_instruction_map = {}
        if instruction_list is not None:
            for instruction in instruction_list:
                instruction_givers_instruction_map[instruction[1].id] = instruction[0]

        stakholder_autonomy_values = []

        

        autonomy_utility = 0.0

        for stakeholder in instruction_givers_instruction_map.keys():
            instructed_action = self.instruction_function_map[instruction_givers_instruction_map[stakeholder]]
            if action.value[0].__name__ == instructed_action:
                autonomy_utility = 1.0
            else:
                autonomy_utility = -1.0
        
            stakholder_autonomy_values.append((stakeholder, autonomy_utility))

        if stakeholder_data['robot']['on_call']:
        
            if action.value[0].__name__ == 'decline_call':
                autonomy_utility = -1.0
            
            
            stakholder_autonomy_values.append(('caller', autonomy_utility))

        return stakholder_autonomy_values

    def get_wellbeing_utility(self, env, stakeholder_data, action, logger):
        """
        Calculating wellbeing values for stakeholders.
        """

        # Simulating next pos and visible lines
        # if action.value[0].__name__ == 'take_call':
        #     next_pos = stakeholder_data['robot']['pos']
        # elif action.value[0].__name__ == 'decline_call' or action.value[0].__name__ == 'decline_instruction_end_call':
        #     next_pos = None
        # else:
        #     next_pos = action.value[0](*action.value[1:], act=False)
        # next_loc = stakeholder_data['robot']['model'].model.get_location(next_pos)
        
        # if next_pos is not None:
        #     visible_stakeholders = stakeholder_data['robot']['model'].model.visible_stakeholders(
        #     center_agent_pos=next_pos, visibility_radius=ROBOT.VISIBLE_DIST)
        #     visible_stakeholders_ids = [stakeholder.id for stakeholder in visible_stakeholders]
        # else:
        
        visible_stakeholders_ids = [stakeholder_id for stakeholder_id in stakeholder_data.keys() if stakeholder_id != 'robot']

        stakholder_wellbeing_values = []

        # Doctor and caregiver have higher wellbeing impact. Family and friends have a 
        # relatively low but considerable impact because the mental health benefits of their 
        # visits.

        # TODO: check the utility dist for doctor and care_giver
        caller_type_util_map = {
            CALLER_TYPE.DOCTOR: 1.0,
            CALLER_TYPE.FAMILY: 0.5,
            CALLER_TYPE.CAREGIVER: 0.8,
            CALLER_TYPE.FRIEND: 0.5,
            CALLER_TYPE.OTHER: 0.0
        }

        interference_util_hit = 0.3


        # for stakeholder, data in stakeholder_data.items():
        #     if stakeholder == 'robot':
        #         continue

        #     wellbeing_util = 0.0


        #     if (stakeholder == stakeholder_data['caller']['calling_resident']) and (stakeholder in visible_stakeholders_ids):
        #         wellbeing_util = caller_type_util_map[stakeholder_data['caller']['type']]
                
        #         # but reduce the wellbeing if the patient is socialising with the care_worker because it might distrupt their session.
        #         if 'care_worker' in visible_stakeholders_ids:
        #             wellbeing_util -= caller_type_util_map[CALLER_TYPE.CAREGIVER]
                    
            
        #         stakholder_wellbeing_values.append((stakeholder, wellbeing_util))

        # Only considering the receiver wellbeing in this implementation
        receiver = stakeholder_data['caller']['calling_resident']

        
        
        if (receiver in visible_stakeholders_ids):
            if (action.value[0].__name__ not in ['decline_call', 'decline_instruction_end_call']):
                wellbeing_util = caller_type_util_map[stakeholder_data['caller']['type']]
                
            else:
                # consider the  negative wellbeing impact of declining of calls
                wellbeing_util = -1*caller_type_util_map[stakeholder_data['caller']['type']]
            
            # Wellbeing is only when receiver is seen.
            stakholder_wellbeing_values.append((receiver, wellbeing_util))

        return stakholder_wellbeing_values
    
    def get_privacy_utility(self, env, stakeholder_data, action, logger):
        """
        Calculating privacy values for stakeholders depending on the location and the privacy preferences.
        """

        # Private levels of the locations: 1 = most private, 0 = least private
        location_privacy_levels = {
            'kitchen': 0.5,
            'living': 0.5,
            'bedroom': 0.8,
            'bedroom_close_bed': 0.8,
            'bathroom': 1.0,
            'other': 0.2
        }


        # Simulating next pos and visible lines
        # if action.value[0].__name__ == 'take_call':
        #     next_pos = stakeholder_data['robot']['pos']
        # elif action.value[0].__name__ == 'decline_call' or action.value[0].__name__ == 'decline_instruction_end_call':
        #     # If the call declined, no one will be seen.
        #     next_pos = None
        # else:
        #     next_pos = action.value[0](*action.value[1:], act=False)

        # next_loc = stakeholder_data['robot']['model'].model.get_location(next_pos)
        # if next_pos:
        #     visible_stakeholders = stakeholder_data['robot']['model'].model.visible_stakeholders(
        #     center_agent_pos=next_pos, visibility_radius=ROBOT.VISIBLE_DIST)
        #     visible_stakeholders_ids = [stakeholder.id for stakeholder in visible_stakeholders if stakeholder.type != 'robot']
        # else:
        visible_stakeholders_ids = [stakeholder_id for stakeholder_id in stakeholder_data.keys() if stakeholder_id not in ['robot', 'caller']]

        call_receiver = stakeholder_data['caller']['calling_resident']

        stakeholder_wellbeing_values = []

        # Privacy should be calculated for all the stakeholders that'll be visible in the next step 
        # (Assuming nobody otherthan robot moved). Caller privacy is not calculated because the caller 
        # is initiated the call and have control.

        for stakeholder in visible_stakeholders_ids:

            location = stakeholder_data[stakeholder]['seen_location']
            role = 'receiver' if stakeholder == call_receiver else '3rd_party'

            other_visible_stakeholders = [item for item in visible_stakeholders_ids if (item != stakeholder)]
            with_company = 'with_company' if len(other_visible_stakeholders) > 0 else 'alone'

            # if stakeholder.id == 'care_worker':
            #     preference = env['worker_preferences'][location][role][with_company]
            # else:
            #     preference = env['resident_preferences'][location][role][with_company]
            rel_location = stakeholder_data[stakeholder]['relative_location']
            preference = stakeholder_data[stakeholder]['preferences'][rel_location][role][with_company]

            privacy_util = 0.0

            if preference:
                pass
            else:
                # End call == will not see anymore.
                if action.value[0].__name__ == 'decline_call' or action.value[0].__name__ == 'decline_instruction_end_call':
                    privacy_util = 1 * location_privacy_levels[rel_location]
                else:
                    try:
                        privacy_util = -1 * location_privacy_levels[rel_location]
                    except KeyError:
                        privacy_util = -1 * location_privacy_levels['other']

            stakeholder_wellbeing_values.append((stakeholder, privacy_util))


        # # If the a patient or care_worker is not visible anymore due to the action, the positive privacy utility given
        # for stakeholder, data in stakeholder_data.items():
        #     if stakeholder == 'robot' or stakeholder == 'caller':
        #         continue

            
        #     if stakeholder not in visible_stakeholders_ids:
        #         location = data['seen_location']
        #         role = 'receiver' if stakeholder == call_receiver else '3rd_party'

        #         other_stakeholders = [item for item in stakeholder_data.keys() if item not in [stakeholder, 'robot', 'caller']]
        #         with_company = 'with_company' if len(other_stakeholders) > 0 else 'alone'

        #         rel_location = data['relative_location']
        #         preference = data['preferences'][rel_location][role][with_company]

        #         privacy_util = 0.0
                
        #         if preference:
        #             pass
        #         else:
        #             try:
        #                 privacy_util = location_privacy_levels[rel_location]
        #             except KeyError:
        #                 privacy_util = location_privacy_levels['other']
                
        #         stakeholder_wellbeing_values.append((stakeholder, privacy_util))

        

        return stakeholder_wellbeing_values

