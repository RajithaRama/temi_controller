import yaml
import ethical_governor.blackboard.loader.loader as loader



class YAMLLoader(loader.Loader):

    def load(self, file_name):
        with open(file_name, 'r') as fp:
            yaml_data = yaml.load(fp, Loader=yaml.FullLoader)
        return yaml_data
