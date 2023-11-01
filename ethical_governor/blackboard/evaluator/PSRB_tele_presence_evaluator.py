import os
import json

import pandas as pd
import numpy as np
import ethical_governor.blackboard.evaluator.evaluator as evaluator

from ethical_governor.blackboard.commonutils.cbr.cbr_tele_presence import CBRTelePresence
from agent_types.tele_presence_robot import Autonomy, Control_Bias, Wellbeing_Pref

CASE_BASE = os.path.join(os.getcwd(), 'ethical_governor', 'blackboard', 'commonutils', 'cbr', 'case_base_gen_telepresence.json')

DUMP_query = False # Set to True to dump the query to a xlsx file. While this is true evaluator will not run as intended.
SCN_RANGE_JSON = os.path.join(os.getcwd(), 'ethical_governor', 'blackboard', 'commonutils', 'cbr', 'scenario_ranges_telepresence.json')

dropping_cases = []

class PSRBEvaluator(evaluator.Evaluator):

    def __init__(self):
        super().__init__()
        
        self.cbr_context_data_feature_map = {
            'robot_location': ['stakeholders', 'robot', 'location'],
            'on_call': ['stakeholders', 'robot', 'on_call'],
            'caller_type': self.get_caller_type, #['stakeholders', 'caller', 'type'],
            'caller_instruction': self.get_caller_instruction,
            'receiver_seen': self.get_receiver_seen,
            'receiver_location': self.get_receiver_location,
            'receiver_preference': self.get_receiver_preference,
            'receiver_with_company': self.get_with_company,
            'worker_seen': self.get_worker_seen,
            'worker_location': self.get_worker_location,
            'worker_preference': self.get_worker_preference,
            'other_patient_seen': self.get_other_patient_seen,
            'other_patient_locations': self.get_other_patient_locations,
            'other_negative_preference_%': self.get_other_negative_pref_percentage,
            'caller_autonomy': self.get_caller_autonomy,
            'receiver_wellbeing': self.get_receiver_wellbeing,
            'receiver_privacy': self.get_receiver_privacy,
            'worker_privacy': self.get_worker_privacy,
            'other_resident_privacy': self.get_other_patient_privacy
        }

        self.expert_db = CBRTelePresence()
        data_df = pd.read_json(CASE_BASE, orient='records', precise_float=True, dtype={
            'other_negative_preference_%': float,
            'caller_autonomy': float,
            "receiver_wellbeing": float,
            "receiver_privacy": float,
            "worker_privacy": float,
            "other_resident_privacy": float,
        })
        # data_df[['caller_autonomy', 'receiver_wellbeing', 'receiver_privacy', 'worker_privacy', 'other_resident_privacy']] = data_df[['caller_autonomy', 'receiver_wellbeing', 'receiver_privacy', 'worker_privacy', 'other_resident_privacy']].astype('float')
        with open(SCN_RANGE_JSON) as scnfp:
                scn_range = json.load(scnfp)
                for scn in dropping_cases:
                    start = int(scn_range[scn]['start'])
                    end = int(scn_range[scn]['end'])
                    case_range = list(range(start, end + 1))
                    data_df = data_df[~data_df['case_id'].isin(case_range)]
        
        self.feature_list = self.expert_db.add_data(data_df)

        if DUMP_query:
            if self.feature_list is None:
                self.feature_list = [col for col in self.cbr_context_data_feature_map.keys()]
            self.queries = pd.DataFrame(columns=self.feature_list)
            self.query_list = [self.queries]

        self.character = {}

    def set_character(self, character):
        self.character = character

    def evaluate(self, data, logger):
        logger.info(__name__ + ' started evaluation using the data in the blackboard.')

        
      
        for action in data.get_actions():
            
            acceptability = 1

            if self.character['autonomy'] is Autonomy.NONE:
                if data.get_table_data(action, 'is_breaking_rule'):
                    acceptability = 0
                # else:
                #     acceptability = 1
                logger.info('Desirability of action ' + str(action.value) + ' : ' + str(acceptability))
                
                data.put_table_data(action=action, column='desirability_score', value=acceptability)
                
                # Explanations
                if acceptability:
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 1' + '| Reason: no rules broken.')
                
                else:
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 0' + '| Reason: rules ' + str(
                            data.get_table_data(action=action, column='breaking_rule_ids')) + ' broken.')



            else:
                logger.info('Evaluating action: ' + str(action))

                expert_opinion, expert_intention = self.get_expert_opinion(action, data, logger)
                logger.info('expert opinion on action ' + str(action) + ' : ' + str(expert_opinion) + ' with ' +
                        str(expert_intention) + ' intention')
                
               # to dump query
                if DUMP_query:
                    data.put_table_data(action=action, column='desirability_score', value=acceptability)
                    continue

                caller_autonomy	= self.get_caller_autonomy(action, data, logger)
                receiver_wellbeing	= self.get_receiver_wellbeing(action, data, logger)
                receiver_privacy = self.get_receiver_privacy(action, data, logger)
                worker_privacy	= self.get_worker_privacy(action, data, logger)
                other_resident_privacy = self.get_other_patient_privacy(action, data, logger)

                rule_broken = data.get_table_data(action=action, column='is_breaking_rule')

                if expert_opinion and not rule_broken:
                    # When rules and expert both accept, accept
                    acceptability = 1
                    data.put_table_data(action=action, column='desirability_score', value=acceptability)
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 1' + '| Reason: no rules broken and '
                                                                                       'accepted by experts.')
                    
                elif not expert_opinion and rule_broken:
                    # When rules and expert both reject, reject
                    acceptability = 0   
                    data.put_table_data(action=action, column='desirability_score', value=acceptability)
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 0' + '| Reason: rules ' + str(
                    data.get_table_data(action=action, column='breaking_rule_ids')) + ' broken and not '
                                                                                      'accepted by experts.')

                elif expert_opinion and rule_broken:
                    # when rules are broken but expert accepts

                    # First check the wellbeing value
                    if self.character['wellbeing_value_preference'] is not Wellbeing_Pref.NONE:
                        if 'receiver_wellbeing' in expert_intention:
                            threshold = (10 - self.character['wellbeing_value_preference'].value)/10
                            if receiver_wellbeing <= threshold:
                                acceptability = 0
                        else:
                            threshold = (self.character['wellbeing_value_preference'].value - 10)/10
                            if receiver_wellbeing <= threshold:
                                acceptability = 0

                    # Then check for the control bias

                    
                    have_control = []
                    not_have_control = []

                    local_vars = dict(locals())
                    for name, value in local_vars.items():
                        if value is not None and (name.endswith('_privacy') or name.endswith('_autonomy')):
                            if self.character['control_bias'][name.split('_')[0]] is not Control_Bias.NONE:
                                if value < 0:
                                    not_have_control.append(name)
                                elif value >= 0:
                                    have_control.append(name)
                            
                    
                    # Commented to improve readability
                    # if len(not_have_control) == 0:
                    #     acceptability = 1

                    if len(have_control) == 0:
                        acceptability = 0
                    elif not set(expert_intention).intersection(set(have_control+not_have_control)):
                        # if the intention has Control_bias.None, the action should not be acceptable.
                        acceptability = 0
                    else:
                        for stakeholder in not_have_control:
                            for stakeholder2 in have_control:
                                if self.character['control_bias'][stakeholder.split('_')[0]].value > self.character['control_bias'][stakeholder2.split('_')[0]].value:
                                    acceptability = 0
                                    break
                                elif self.character['control_bias'][stakeholder.split('_')[0]].value == self.character['control_bias'][stakeholder2.split('_')[0]].value:
                                    # In a tie, if the autonomy is low, rules have the authority. when autonomy is high knowledge base has it.
                                    if self.character['autonomy'] == Autonomy.LOW:
                                        acceptability = 0
                                        break
                                        
                            # if the control bias is high, the stakeholder should not get a very high privacy breach.
                            if '_privacy' in stakeholder:
                                lower_threshold = (self.character['control_bias'][stakeholder.split('_')[0]].value - 10)/10
                                if eval(stakeholder) <= lower_threshold:
                                    acceptability = 0

                    
                    # TODO: debug and complete.
                    data.put_table_data(action=action, column='desirability_score', value=acceptability)

                    # Explanations
                    if acceptability:
                        logger.info("Action " + action.value[0].__name__ + ' desirability: 1' + '| Reason: rules ' + str(
                            data.get_table_data(action=action, column='breaking_rule_ids')) + ' broken, but accepted by '
                            'experts. Since it increases ' + str(expert_intention) + ' values greatly deemed accepted by PSRB system.')
                    
                    else:
                        logger.info("Action " + action.value[0].__name__ + ' desirability: 0' + '| Reason: rules ' + str(
                            data.get_table_data(action=action, column='breaking_rule_ids')) + ' broken, but accepted by '
                            'experts. However, the value tradeoff is not satisfactory to bend the rule.')
                
                
                else:
                    # When rules are not broken but expert rejects
                    if 'receiver_wellbeing' in expert_intention:
                        lower_threshold = (self.character['wellbeing_value_preference'].value - 10)/10
                        if receiver_wellbeing <= lower_threshold:
                            acceptability = 0

                    # Then check for reciever intended the control bias
                    local_vars = dict(locals())
                    for name, value in local_vars.items():
                        if name in expert_intention:
                            lower_threshold = (self.character['control_bias'][name.split('_')[0]].value - 10)/10
                            if value <= lower_threshold:
                                acceptability = 0
                                break

                    data.put_table_data(action=action, column='desirability_score', value=acceptability)

                    #Explanations
                    if acceptability:
                        logger.info("Action " + action.value[0].__name__ + ' desirability: 1' + '| Reason: no rules broken, but not accepted by '
                            'experts. However, PSRB system suggest the value tradeoff not enough to bend the rule.')
                        
                    else:
                        logger.info("Action " + action.value[0].__name__ + ' desirability: 0 | Reason: no rules broken, but not accepted by '
                            'experts. Since it decreases ' + str(expert_intention) + ' values too much, deemed not accepted by '
                                                                                                                            'PSRB system.')


    def get_expert_opinion(self, action, data, logger):
        query = self.generate_query(action, data, logger)
        if DUMP_query:
            self.dump_query(query)
            vote = 1
            intention = 'test'
        else:
            neighbours_with_dist = self.expert_db.get_neighbours_with_distances(query=query, logger=logger)
            logger.info('closest neighbours to the case are: ' + str(neighbours_with_dist))
            vote, intention = self.expert_db.distance_weighted_vote(neighbours_with_dist=neighbours_with_dist,
                                                                    threshold=3,
                                                                    logger=logger)

        return vote, intention
    
    
    def generate_query(self, action, data, logger):
        logger.info(__name__ + ' started query generation using the data in the blackboard.')
        query = pd.DataFrame()
        query['action'] = [action.value[0].__name__]

        control_pref_exclude_list = [x for x, y in self.character['control_bias'].items() if y is Control_Bias.NONE]
        wellbeing_pref = self.character['wellbeing_value_preference'].value


        for feature, feature_path in self.cbr_context_data_feature_map.items():
            
            # Skip control preference features if the character has no control preference
            skip = False
            feature_tokens = feature.split('_')
            if feature_tokens[-1] in ['privacy', 'autonomy']:
                for item in control_pref_exclude_list:
                    if item.split('_') == feature_tokens[:-1]:
                        skip = True
                        break
            if wellbeing_pref == 0 and feature_tokens[-1] == 'wellbeing':
                skip = True
            
            if skip:
                continue

            if callable(feature_path):
                value = feature_path(action, data, logger)
            elif isinstance(feature_path, list):
                value = data.get_data(feature_path)
            else:
                raise ValueError('Invalid feature path')
            
            if value is not None:
                query[feature] = [value]
            else:
                if DUMP_query:
                    query[feature] = [value]
                continue
        return query
    
    def dump_query(self, query):
        self.query_list.append(query)
        self.queries = pd.concat(self.query_list, ignore_index=True)
        self.queries.to_excel('query_dump.xlsx', sheet_name='query', index=False)


    ######################################
    # Feature extraction functions
    ######################################

    def get_caller_type(self, action, data, logger):
        caller_type = data.get_data(['stakeholders', 'caller', 'type'])
        caller_type_str = str(caller_type)
        if caller_type == None:
            return None
        else:
            return caller_type_str

    def get_caller_instruction(self, action, data, logger):
        instruction_list = data.get_data(['stakeholders', 'robot', 'instruction_list'])
        if instruction_list is None:
            return None
        
        for instruction in instruction_list:
            if instruction[1].id == 'caller':
                return instruction[0]
        return None
            

    def get_receiver_seen(self, action, data, logger):
        receiver = data.get_data(['stakeholders', 'caller', 'calling_resident'])
        if receiver is None:
            return None
        for table_col in data.get_table_col_names():
            if receiver in table_col:
                return True
            
        return False
    

    def get_receiver_location(self, action, data, logger):
        if self.get_receiver_seen(action, data, logger):
            receiver = data.get_data(['stakeholders', 'caller', 'calling_resident'])
            location = data.get_data(['stakeholders', receiver, 'seen_location'])
            return location
        else:
            return None
    

    def get_receiver_preference(self, action, data, logger):
        if self.get_receiver_seen(action, data, logger):
            receiver = data.get_data(['stakeholders', 'caller', 'calling_resident'])
            preferences = data.get_data(['stakeholders', receiver, 'preferences'])
            
            location = data.get_data(['stakeholders', receiver, 'relative_location'])
            
            other_visible_stakeholders_ids = [stakeholder_id for stakeholder_id in data.get_data(['stakeholders']).keys() if stakeholder_id not in ['robot', 'caller', receiver]]
            with_company = 'with_company' if len(other_visible_stakeholders_ids) > 0 else 'alone'
            
            
            preference = preferences[location]['receiver'][with_company]
            return preference
        else:
            return None
    

    def get_with_company(self, action, data, logger):
        if self.get_receiver_seen(action, data, logger):
            receiver = data.get_data(['stakeholders', 'caller', 'calling_resident'])
            other_visible_stakeholders_ids = [stakeholder_id for stakeholder_id in data.get_data(['stakeholders']).keys() if stakeholder_id not in ['robot', 'caller', receiver]]
            with_company = 'with_company' if len(other_visible_stakeholders_ids) > 0 else 'alone'
            return with_company
        else:
            return None

    def get_worker_seen(self, action, data, logger):
        for id in data.get_data(['stakeholders']).keys():
            if id == 'care_worker':
                return True
        return False
    
    
    def get_worker_location(self, action, data, logger):
        if self.get_worker_seen(action, data, logger):
            return data.get_data(['stakeholders', 'care_worker', 'seen_location'])
        else:
            return None

    def get_worker_preference(self, action, data, logger):
        if self.get_worker_seen(action, data, logger):
            preferences = data.get_data(['stakeholders', 'care_worker', 'preferences'])

            location = data.get_data(['stakeholders', 'care_worker', 'relative_location'])
            role = '3rd_party'

            other_visible_stakeholders_ids = [stakeholder_id for stakeholder_id in data.get_data(['stakeholders']).keys() if stakeholder_id not in ['robot', 'caller', 'care_worker']]
            with_company = 'with_company' if len(other_visible_stakeholders_ids) > 0 else 'alone'

            preference = preferences[location][role][with_company]
            return preference
        else:
            return None
    
    def get_other_patient_seen(self, action, data, logger):
        stakeholder_data = data.get_data(['stakeholders'])
        try:
            receiver = stakeholder_data['caller']['calling_resident']
        except KeyError:
            receiver = None
        
        for id in stakeholder_data.keys():
            if id not in ['robot', 'caller', receiver, 'care_worker']:
                return True
        return False
    
    def get_other_patient_locations(self, action, data, logger):
        if self.get_other_patient_seen(action, data, logger):
            stakeholder_data = data.get_data(['stakeholders'])
            other_patient_locations = []
            for id in stakeholder_data.keys():
                if id not in ['robot', 'caller', data.get_data(['stakeholders', 'caller', 'calling_resident']), 'care_worker']:
                    other_patient_locations.append(stakeholder_data[id]['seen_location'])
            return other_patient_locations
        else:
            return None
        
    def get_other_negative_pref_percentage(self, action, data, logger):
        if self.get_other_patient_seen(action, data, logger):
            other_patient_number = 0
            stakeholder_data = data.get_data(['stakeholders'])
            other_negative_pref_count = 0
            for id in stakeholder_data.keys():
                if id not in ['robot', 'caller', data.get_data(['stakeholders', 'caller', 'calling_resident']), 'care_worker']:
                    preferences = stakeholder_data[id]['preferences']
                    location = stakeholder_data[id]['relative_location']
                    role = '3rd_party'
                    if len([stakeholder_id for stakeholder_id in stakeholder_data.keys() if stakeholder_id not in ['robot', 'caller', id]]) > 0:
                        with_company = 'with_company' 
                    else:
                        with_company = 'alone'
                    preference = preferences[location][role][with_company]
                    if not preference:
                        other_negative_pref_count += 1
                    other_patient_number += 1
            return np.float64(other_negative_pref_count / other_patient_number)
        else:
            return None
    
    def get_caller_autonomy(self, action, data, logger):
        try:
            return np.float64(data.get_table_data(action, 'caller_autonomy'))
        except KeyError:
            return None
        
    def get_receiver_wellbeing(self, action, data, logger):
        if self.get_receiver_seen(action, data, logger):
            receiver = data.get_data(['stakeholders', 'caller', 'calling_resident'])
            return np.float64(data.get_table_data(action, receiver + '_wellbeing'))
        else:
            return None

    def get_receiver_privacy(self, action, data, logger):
        if self.get_receiver_seen(action, data, logger):
            receiver = data.get_data(['stakeholders', 'caller', 'calling_resident'])
            return np.float64(data.get_table_data(action, receiver + '_privacy'))
        else:
            return None
    
    def get_worker_privacy(self, action, data, logger):
        if self.get_worker_seen(action, data, logger):
            return np.float64(data.get_table_data(action, 'care_worker_privacy'))
        else:
            return None
        
    def get_other_patient_privacy(self, action, data, logger):
        """
            Get the maximum breach of privacy of the other patients
        """
        if self.get_other_patient_seen(action, data, logger):
            reciever = data.get_data(['stakeholders', 'caller', 'calling_resident'])
            min_privacy = 1
            for col in data.get_table_col_names():
                if col.endswith('_privacy'):
                    stakeholder = col.replace('_privacy', '')
                    if stakeholder not in ['robot', 'caller', reciever, 'care_worker']:
                        privacy = data.get_table_data(action, col)
                        if privacy < min_privacy:
                            min_privacy = privacy
            return np.float64(min_privacy)      
            
        else:
            return None
            
        