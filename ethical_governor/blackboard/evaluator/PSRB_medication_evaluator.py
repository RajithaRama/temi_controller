import os
import json
import pandas as pd
import numpy as np

import ethical_governor.blackboard.evaluator.evaluator as evaluator
import ethical_governor.blackboard.ethicaltests.medication_utilitarian_test as medication_utilitarian_test 

from Models.home_medication import MedImpact

from ethical_governor.blackboard.commonutils.cbr.cbr_medication import CBRMedication

CASE_BASE = os.path.join(os.getcwd(), 'ethical_governor', 'blackboard', 'commonutils', 'cbr', 'case_base_gen_medication.json')
SCN_RANGE_JSON = os.path.join(os.getcwd(), 'ethical_governor', 'blackboard', 'commonutils', 'cbr', 'scenario_ranges_medication.json')

DUMP_query = False # Set to True to dump the query to a xlsx file. While this is true evaluator will not run as intended.

cbr_context_data_feature_map = {
    'took_meds': ['stakeholders', 'patient_0', 'took_meds'],
    'med_name': ['stakeholders', 'patient_0', 'attached_reminders', 'med_name'],
    'med_type': ['environment', 'Medication_info', ['stakeholders', 'patient_0', 'attached_reminders', 'med_name'], 'type'],
    'med_impact': ['environment', 'Medication_info', ['stakeholders', 'patient_0', 'attached_reminders', 'med_name'], 'impact'],
    'time_since_last_reminder': ['stakeholders', 'patient_0', 'attached_reminders', 'time'],
    'state': ['stakeholders', 'patient_0', 'attached_reminders', 'state'],
    'no_of_missed_doses':['stakeholders', 'patient_0', 'no_of_missed_doses'],
    'no_of_followups':['stakeholders', 'patient_0', 'attached_reminders', 'no_of_followups'],
    'no_of_snoozes': ['stakeholders', 'patient_0', 'attached_reminders', 'no_of_snoozes'],
    'user_response': ['stakeholders', 'robot', 'instruction_list', 0, 0],
    'time_of_day': ['environment', 'time_of_day']
}

cbr_table_data_features = {
    'follower_autonomy': 'patient_0_autonomy', 'follower_wellbeing': 'patient_0_wellbeing', 'wellbeing_probability': 'patient_0_wellbeing_probability'
}

# dropping_cases = ["Scn6"]
dropping_cases = []



class PSRBEvaluator(evaluator.Evaluator):

    def __init__(self):
        super().__init__()
        self.expert_db = CBRMedication()
        with open(CASE_BASE) as fp:
            data_df = pd.read_json(CASE_BASE, orient='records', precise_float=False)
            with open(SCN_RANGE_JSON) as scnfp:
                scn_range = json.load(scnfp)
                for scn in dropping_cases:
                    start = int(scn_range[scn]['start'])
                    end = int(scn_range[scn]['end'])
                    case_range = list(range(start, end + 1))
                    data_df = data_df[~data_df['case_id'].isin(case_range)]

            data_df[['follower_autonomy', 'follower_wellbeing', 'wellbeing_probability']] = data_df[['follower_autonomy', 'follower_wellbeing', 'wellbeing_probability']].astype(float)
            self.feature_list = self.expert_db.add_data(data_df)

        if DUMP_query:
            self.queries = pd.DataFrame(columns=self.feature_list)
            self.query_list = [self.queries]

        self.character = {}
        

    def set_character(self, character):
        self.character = character

    def evaluate(self, data, logger):
        logger.info(__name__ + ' started evaluation using the data in the blackboard.')
        self.score = {}
        # for action in data.get_actions():
        #     if data.get_table_data(action, 'is_breaking_rule'):
        #         self.score[action] = 0
        #     else:
        #         self.score[action] = 1
        #     logger.info('Desirability of action ' + str(action.value) + ' : ' + str(self.score[action]))


        for action in data.get_actions():
            logger.info('Evaluating action: ' + str(action))
            expert_opinion, expert_intention = self.get_expert_opinion(action, data, logger)
            logger.info('expert opinion on action ' + str(action) + ' : ' + str(expert_opinion) + ' with ' +
                        str(expert_intention) + ' intention')
            
            

            acceptability = 1

            wellbeing = data.get_table_data(action, 'patient_0_wellbeing')
            autonomy = data.get_table_data(action, 'patient_0_autonomy')
            wellbeing_probability = data.get_table_data(action, 'patient_0_wellbeing_probability')
            wellbeing_prob_dist = data.get_table_data(action, 'patient_0_wellbeing_distribution')

            # Calculating Expectation values for wellbeing
            resolution = medication_utilitarian_test.RESOLUTION
            utility_range = np.linspace(-1, 1, int(2 / resolution + 1)).round(5).tolist()
            
            expectation_values = []

            for i in range(len(utility_range) - 1):
                #Calculating expectation values only for negative utility values 
                #(because positive utility == chance, not risk) (ref: Sven ove Hansson - The ethics of risk)
                if utility_range[i] < 0:
                    utility = (utility_range[i] + utility_range[i+1])/2                
                    expectation_values.append(abs(wellbeing_prob_dist[i] * utility))

 
            rule_broken = data.get_table_data(action=action, column='is_breaking_rule')

            if expert_opinion and not rule_broken:
                # When rules and expert both accept, accept
                data.put_table_data(action=action, column='desirability_score', value=1)
                logger.info("Action " + action.value[0].__name__ + ' desirability: 1' + '| Reason: no rules broken and '
                                                                                       'accepted by experts.')
                
            elif not expert_opinion and rule_broken:
                # When rules and expert both reject, reject
                data.put_table_data(action=action, column='desirability_score', value=0)
                logger.info("Action " + action.value[0].__name__ + ' desirability: 0' + '| Reason: rules ' + str(
                    data.get_table_data(action=action, column='breaking_rule_ids')) + ' broken and not '
                                                                                      'accepted by experts.')
                
            elif expert_opinion and rule_broken:
                # when rules broken but accepted by expert
                
                # Risk threshold = threshold for expectation value of wellbeing
                r = self.character['risk_propensity']
                # risk_threshold = self.character['risk_propensity']/10
                risk_threshold = ((np.exp(r/4.17) - 1)/10).round(2)
                
                # Accessing autonomy acceptability
                if 'autonomy' in expert_intention:
                    threshold = (10 - self.character['autonomy'])/10
                    if autonomy < threshold:
                        acceptability = 0
                else:
                    threshold = (self.character['autonomy'] - 10)/10
                    if autonomy < threshold:
                        acceptability = 0

                # Accessing wellbeing acceptability ( Considering the highest possible utility value)
                if 'wellbeing' in expert_intention:
                    threshold = (10 - self.character['wellbeing'])/10
                    if wellbeing < threshold:
                        acceptability = 0
                else:
                    threshold = (self.character['wellbeing'] - 10)/10
                    if wellbeing < threshold:
                        acceptability = 0

                # Accessing risk acceptability
                risk_acceptable = True
                if acceptability:
                    for expectation_value in expectation_values:
                        if expectation_value > risk_threshold:
                            acceptability = 0
                            risk_acceptable = False
                    
                data.put_table_data(action=action, column='desirability_score', value=acceptability)

                # Explanations
                if acceptability:
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 1' + '| Reason: rules ' + str(
                        data.get_table_data(action=action, column='breaking_rule_ids')) + ' broken, but accepted by '
                        'experts. Since it increases ' + str(expert_intention) + ' values greatly and the outcome is ' 
                        'within accepted risk levels, deemed accepted by PSRB system.')
                    
                elif not risk_acceptable:
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 0' + '| Reason: rules ' + str(
                        data.get_table_data(action=action, column='breaking_rule_ids')) + ' broken, but accepted by '
                        'experts. The value tradeoff is satisfactory, but the risk taken by the action is not acceptable to bend the rule.')
                
                else:
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 0' + '| Reason: rules ' + str(
                        data.get_table_data(action=action, column='breaking_rule_ids')) + ' broken, but accepted by '
                        'experts. However, the value tradeoff is not satisfactory to bend the rule.')


            elif not expert_opinion and not rule_broken:
                
                # when the action obeys the rules, but not accepted by experts
                if 'autonomy' in expert_intention:
                    lower_threshold = (self.character['autonomy'] - 10)/10
                    if autonomy < lower_threshold:
                        acceptability = 0

                if 'wellbeing' in expert_intention:
                    lower_threshold = (self.character['wellbeing'] - 10)/10
                    if wellbeing < lower_threshold:
                        acceptability = 0
                
                risk_acceptable = True
                if acceptability:
                    r = self.character['risk_propensity']
                    # risk_threshold = self.character['risk_propensity']/10
                    risk_threshold = ((np.exp(r/4.17) - 1)/10).round(2)
                    for expectation_value in expectation_values:
                        if expectation_value > risk_threshold:
                            acceptability = 0
                            risk_acceptable = False

                data.put_table_data(action=action, column='desirability_score', value=acceptability)

                #Explanations
                if acceptability:
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 1' + '| Reason: no rules broken, but not accepted by '
                        'experts. However, PSRB system suggest the value tradeoff not enough to bend the rule.')
                    
                elif not risk_acceptable:
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 0 | Reason: no rules broken, but not accepted by '
                        'experts. Since the action outcomes introduces a high risk, deemed not accepted by the PSRB system.')
                    
                else:
                    logger.info("Action " + action.value[0].__name__ + ' desirability: 0 | Reason: no rules broken, but not accepted by '
                        'experts. Since it decreases ' + str(expert_intention) + ' values too much, deemed not accepted by '
                                                                                                                       'PSRB system.')


            if DUMP_query:
                data.put_table_data(action=action, column='desirability_score', value=1) 
            

    
    def get_expert_opinion(self, action, data, logger):
        query = self.generate_query(action, data)
        # print(query)
        if DUMP_query:
            self.dump_query(query)
            vote = 1
            intention = 'test'
        else:
            neighbours_with_dist = self.expert_db.get_neighbours_with_distances(query=query, logger=logger)
            logger.info('closest neighbours to the case are: ' + str(neighbours_with_dist))
            vote, intention = self.expert_db.distance_weighted_vote(neighbours_with_dist=neighbours_with_dist, threshold=3,
                                                                logger=logger)
        
        return vote, intention

    def generate_query(self, action, data):
        query = pd.DataFrame()
        for feature in self.feature_list:
            if feature in ['case_id', 'acceptability', 'intention']:
                continue

            if feature == 'action':
                query[feature] = [action.value[0].__name__]
                continue
            try:
                path = cbr_context_data_feature_map[feature]
            except KeyError:
                path = None
            if path:
                if feature == "time_since_last_reminder":
                    if data.get_data(path) is not None:
                        last_remind_time = data.get_data(path)
                        value = data.get_data(['environment', 'time']) - last_remind_time
                    else:
                        value = None
                elif feature == "took_meds":
                    if data.get_data(path) == True:
                        value = 1
                    else:
                        value = 0
                elif feature == "med_impact" and type(data.get_data(path)) == MedImpact:
                    value = data.get_data(path).value
                else:
                    value = data.get_data(path)
            else:
                path = cbr_table_data_features[feature]
                value = data.get_table_data(action=action, column=path)

            if value == None:
                if DUMP_query:
                    query[feature] = [value]
                continue

            query[feature] = [value]
            
        return query
    
    def dump_query(self, query):

        self.query_list.append(query)
        # self.queries = self.queries.append(query, ignore_index=True)
        self.queries = pd.concat(self.query_list, ignore_index=True)
        self.queries.to_excel('query_dump.xlsx', sheet_name='query')